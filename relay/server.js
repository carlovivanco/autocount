const WebSocket = require('ws');

const PORT      = process.env.PORT       || 3000;
const PI_TOKEN  = process.env.PI_TOKEN   || 'autocount-pi-secret';

const wss = new WebSocket.Server({ port: PORT });

let piSocket    = null;
let lastPiState = null; // always kept as full state (includes today_events)
const frontendClients = new Set();

function mergeState(incoming) {
  if (!lastPiState) { lastPiState = incoming; return; }
  const state   = JSON.parse(lastPiState);
  const parsed  = JSON.parse(incoming);
  if (parsed.count          !== undefined) state.count          = parsed.count;
  if (parsed.peak_prediction !== undefined) state.peak_prediction = parsed.peak_prediction;
  if (parsed.today_events   !== undefined) state.today_events   = parsed.today_events;
  if (parsed.midnight_reset)               state.today_events   = [];
  lastPiState = JSON.stringify(state);
}

function broadcast(message) {
  for (const client of frontendClients) {
    if (client.readyState === WebSocket.OPEN) client.send(message);
  }
}

wss.on('connection', (ws, req) => {
  const token = new URL(req.url, 'ws://localhost').searchParams.get('token');

  if (token === PI_TOKEN) {
    // ── Pi ─────────────────────────────────────────
    if (piSocket) piSocket.terminate();
    piSocket = ws;
    console.log('[Pi] Conectada');
    broadcast(JSON.stringify({ pi_connected: true }));

    ws.on('message', (data) => {
      const str = data.toString();
      try {
        const parsed = JSON.parse(str);
        if (!parsed.excel_b64) mergeState(str); // keep full state; skip large blobs
      } catch {}
      broadcast(str);
    });

    ws.on('close', () => {
      if (piSocket === ws) piSocket = null;
      console.log('[Pi] Desconectada');
      broadcast(JSON.stringify({ pi_connected: false }));
    });

    ws.on('error', (e) => console.error('[Pi]', e.message));

  } else {
    // ── Frontend ────────────────────────────────────
    frontendClients.add(ws);
    console.log(`[Frontend] +1 (${frontendClients.size} activos)`);

    // Send current state immediately so UI shows count on load
    if (lastPiState) ws.send(lastPiState);
    ws.send(JSON.stringify({ pi_connected: piSocket !== null }));

    ws.on('message', (data) => {
      if (piSocket && piSocket.readyState === WebSocket.OPEN)
        piSocket.send(data.toString());
    });

    ws.on('close', () => {
      frontendClients.delete(ws);
      console.log(`[Frontend] -1 (${frontendClients.size} activos)`);
    });

    ws.on('error', (e) => console.error('[Frontend]', e.message));
  }
});

console.log(`Relay escuchando en puerto ${PORT}`);
