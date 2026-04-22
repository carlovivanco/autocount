#!/bin/bash
# arrancar.sh — Inicia el backend del gym, actualiza Vercel con la nueva URL
# del túnel y lanza el redeploy automáticamente.
#
# Configuración inicial (llenar UNA sola vez):
#   VERCEL_TOKEN   → vercel.com/account/tokens → Create Token
#   PROJECT_ID     → vercel.com/<tu-proyecto>/settings → Project ID
#   ENV_VAR_ID     → corre este comando para obtenerlo:
#                    curl -H "Authorization: Bearer <TU_TOKEN>" \
#                      "https://api.vercel.com/v9/projects/<PROJECT_ID>/env" \
#                      | python3 -m json.tool | grep -A2 "VITE_WS_URL"
#   DEPLOY_HOOK    → vercel.com/<proyecto>/settings/git → Deploy Hooks → crear uno

set -e

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
VERCEL_TOKEN="TU_TOKEN_AQUI"
PROJECT_ID="TU_PROJECT_ID_AQUI"
ENV_VAR_ID="TU_ENV_VAR_ID_AQUI"
DEPLOY_HOOK="TU_DEPLOY_HOOK_URL_AQUI"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$SCRIPT_DIR/../contador_cruce_imx500.py"
CF_LOG="/tmp/cloudflared.log"
# ──────────────────────────────────────────────────────────────────────────────

echo "[gym-tec] Iniciando servicios..."

# Limpiar procesos anteriores
pkill -f cloudflared     2>/dev/null || true
pkill -f contador_cruce  2>/dev/null || true
sleep 2

# Iniciar túnel en background y capturar log
cloudflared tunnel --url ws://localhost:8765 > "$CF_LOG" 2>&1 &

# Esperar URL (máximo 30 segundos)
echo "[gym-tec] Esperando URL de Cloudflare..."
TUNNEL_URL=""
for i in $(seq 1 30); do
    TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$CF_LOG" 2>/dev/null | head -1)
    [ -n "$TUNNEL_URL" ] && break
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo "[gym-tec] ERROR: no se obtuvo URL del túnel. Revisa cloudflared."
    exit 1
fi

WSS_URL="${TUNNEL_URL/https:/wss:}"
echo "[gym-tec] Túnel activo: $WSS_URL"

# Actualizar VITE_WS_URL en Vercel
echo "[gym-tec] Actualizando variable de entorno en Vercel..."
curl -s -X PATCH \
    -H "Authorization: Bearer $VERCEL_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"value\": \"$WSS_URL\", \"target\": [\"production\"]}" \
    "https://api.vercel.com/v9/projects/$PROJECT_ID/env/$ENV_VAR_ID" > /dev/null

# Disparar redeploy en Vercel (~1-2 min)
echo "[gym-tec] Redeploy de Vercel iniciado (listo en ~1 min)..."
curl -s -X POST "$DEPLOY_HOOK" > /dev/null

# Iniciar backend (en foreground — systemd lo monitorea aquí)
echo "[gym-tec] Iniciando backend Python..."
exec python3 "$BACKEND"
