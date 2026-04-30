#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Autocount Pi – setup.sh
#  Uso: bash setup.sh [SCRIPT]
#
#  SCRIPT : archivo Python a ejecutar (default: contador_cruce_imx500.py)
#
#  Qué hace:
#    1. Instala Tailscale Funnel (URL estable sin port forwarding)
#    2. Crea y activa un servicio systemd que arranca el contador
#       automáticamente al encender la Pi y lo reinicia si crashea
# ─────────────────────────────────────────────────────────────
set -e

SCRIPT="${1:-contador_cruce_imx500.py}"
WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="$(whoami)"
PYTHON="$(command -v python3)"
SERVICE_NAME="autocount"

echo ""
echo "▶ Configurando en: $WORKDIR"
echo "▶ Script:          $SCRIPT"
echo "▶ Usuario:         $RUN_USER"
echo ""

# ── 1. Tailscale ────────────────────────────────────────────
echo "[1/3] Configurando Tailscale Funnel..."

if ! command -v tailscale &>/dev/null; then
  echo "  Instalando Tailscale..."
  curl -fsSL https://tailscale.com/install.sh | sh
else
  echo "  ✓ Tailscale ya instalado"
fi

sudo systemctl enable --now tailscaled

# Activar funnel para el puerto 8765 (persiste entre reinicios)
sudo tailscale funnel --bg 8765
echo "  ✓ Funnel activo en puerto 8765"

# Obtener URL
FUNNEL_HOST=$(tailscale status --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('Self', {}).get('DNSName', '').rstrip('.'))
")
echo ""
echo "  URL WebSocket estable:"
echo "    wss://${FUNNEL_HOST}"
echo ""
echo "  ► Copia esta URL — la necesitas en Vercel (VITE_WS_URL)"
echo ""

# ── 2. Servicio systemd ─────────────────────────────────────
echo "[2/3] Creando servicio systemd..."

# Detectar entorno virtual si existe
if [ -f "$WORKDIR/venv/bin/python3" ]; then
  PYTHON="$WORKDIR/venv/bin/python3"
  echo "  ✓ Virtualenv detectado: $PYTHON"
fi

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Autocount Gimnasio – Contador de personas IMX500
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${WORKDIR}
ExecStart=${PYTHON} ${WORKDIR}/${SCRIPT}
Restart=always
RestartSec=10
StartLimitIntervalSec=0

[Install]
WantedBy=multi-user.target
EOF

# ── 3. Habilitar y arrancar ─────────────────────────────────
echo "[3/3] Activando servicio del contador..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

sleep 2
STATUS=$(sudo systemctl is-active ${SERVICE_NAME})
if [ "$STATUS" = "active" ]; then
  echo "  ✓ Servicio activo y corriendo"
else
  echo "  ✗ El servicio no arrancó. Revisa con:"
  echo "    sudo journalctl -u ${SERVICE_NAME} -n 30"
  exit 1
fi

# ── Resumen ─────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Setup completado"
echo ""
echo "  En Vercel, pon esta variable de entorno:"
echo "    VITE_WS_URL = wss://${FUNNEL_HOST}"
echo ""
echo "  Comandos útiles:"
echo "    sudo systemctl status ${SERVICE_NAME}    # estado del contador"
echo "    sudo systemctl restart ${SERVICE_NAME}   # reiniciar contador"
echo "    sudo journalctl -u ${SERVICE_NAME} -f    # logs en vivo"
echo "    tailscale funnel status                  # estado del túnel"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
