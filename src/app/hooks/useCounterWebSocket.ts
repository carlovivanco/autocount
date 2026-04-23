import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined) ?? 'ws://raspberrypi.local:8765';

export type TodayEvent = { tipo: string; timestamp: string };

interface CounterWebSocketResult {
  count: number;
  connected: boolean;
  peakPrediction: string | null;
  todayEvents: TodayEvent[] | null;
  sendCommand: (cmd: string) => void;
}

function triggerExcelDownload(b64: string, filename: string) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const blob = new Blob([bytes], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function useCounterWebSocket(
  onDelta: (delta: number) => void,
): CounterWebSocketResult {
  const [count, setCount] = useState(0);
  const [connected, setConnected] = useState(false);
  const [peakPrediction, setPeakPrediction] = useState<string | null>(null);
  const [todayEvents, setTodayEvents] = useState<TodayEvent[] | null>(null);
  const prevCountRef = useRef(0);
  const isFirstMessage = useRef(true);
  const onDeltaRef = useRef(onDelta);
  const wsRef = useRef<WebSocket | null>(null);
  onDeltaRef.current = onDelta;

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let unmounted = false;

    function connect() {
      if (unmounted) return;
      isFirstMessage.current = true;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!unmounted) setConnected(true);
      };

      ws.onmessage = (event) => {
        if (unmounted) return;
        try {
          const data = JSON.parse(event.data as string) as Record<string, unknown>;
          if ('count' in data) {
            const newCount = typeof data.count === 'number' ? data.count : 0;

            if ('midnight_reset' in data && data.midnight_reset) {
              // Midnight reset — clear log, update count, no delta
              prevCountRef.current = 0;
              setCount(0);
              setTodayEvents([]);
              return;
            }

            if (isFirstMessage.current) {
              // Initial sync — no delta, load today's events from backend
              if ('today_events' in data && Array.isArray(data.today_events)) {
                setTodayEvents(data.today_events as TodayEvent[]);
              }
            } else {
              const delta = newCount - prevCountRef.current;
              if (delta !== 0) onDeltaRef.current(delta);
            }

            isFirstMessage.current = false;
            prevCountRef.current = newCount;
            setCount(newCount);

            if ('peak_prediction' in data) {
              setPeakPrediction(typeof data.peak_prediction === 'string' ? data.peak_prediction : null);
            }
          } else if ('excel_b64' in data) {
            triggerExcelDownload(data.excel_b64 as string, data.filename as string);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!unmounted) {
          setConnected(false);
          wsRef.current = null;
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      unmounted = true;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  const sendCommand = useCallback((cmd: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ command: cmd }));
    }
  }, []);

  return { count, connected, peakPrediction, todayEvents, sendCommand };
}
