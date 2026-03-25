import { useState, useEffect, useRef } from 'react';

const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined) ?? 'ws://raspberrypi.local:8765';

interface CounterWebSocketResult {
  count: number;
  connected: boolean;
}

/**
 * Connects to the Raspberry Pi WebSocket server and streams the live
 * person count. Automatically reconnects on disconnect.
 *
 * @param onDelta - called whenever the count changes; delta > 0 means entries,
 *                  delta < 0 means exits. May be called with |delta| > 1 if
 *                  multiple people cross at once.
 */
export function useCounterWebSocket(
  onDelta: (delta: number) => void,
): CounterWebSocketResult {
  const [count, setCount] = useState(0);
  const [connected, setConnected] = useState(false);
  const prevCountRef = useRef(0);
  const onDeltaRef = useRef(onDelta);
  onDeltaRef.current = onDelta;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let unmounted = false;

    function connect() {
      if (unmounted) return;

      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (!unmounted) setConnected(true);
      };

      ws.onmessage = (event) => {
        if (unmounted) return;
        try {
          const data = JSON.parse(event.data as string) as { count: number };
          const newCount = typeof data.count === 'number' ? data.count : 0;
          const delta = newCount - prevCountRef.current;
          prevCountRef.current = newCount;
          setCount(newCount);
          if (delta !== 0) {
            onDeltaRef.current(delta);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!unmounted) {
          setConnected(false);
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      unmounted = true;
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return { count, connected };
}
