#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Autocount Pi – setup.sh
#  Uso: bash setup.sh <RELAY_URL> <PI_TOKEN> [SCRIPT]
#
#  RELAY_URL : URL del relay en la nube  (wss://autocount-relay.onrender.com)
#  PI_TOKEN  : token secreto compartido  (autocount-pi-secret)
#  SCRIPT    : archivo Python a ejecutar (default: contador_cruce_imx500_trained.py)
# ─────────────────────────────────────────────────────────────
set -e

RELAY_URL="${1:?Falta RELAY_URL. Uso: bash setup.sh RELAY_URL PI_TOKEN}"
PI_TOKEN="${2:?Falta PI_TOKEN.  Uso: bash setup.sh RELAY_URL PI_TOKEN}"
SCRIPT="${3:-contador_cruce_imx500_trained.py}"

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="$(whoami)"
PYTHON="$(command -v python3)"
SERVICE_NAME="autocount"

echo ""
echo "▶ Configurando en: $WORKDIR"
echo "▶ Script:          $SCRIPT"
echo "▶ Relay:           $RELAY_URL"
echo ""

# Detectar entorno virtual si existe
if [ -f "$WORKDIR/yolo-env/bin/python3" ]; then
  PYTHON="$WORKDIR/yolo-env/bin/python3"
  echo "  ✓ yolo-env detectado: $PYTHON"
elif [ -f "$WORKDIR/venv/bin/python3" ]; then
  PYTHON="$WORKDIR/venv/bin/python3"
  echo "  ✓ venv detectado: $PYTHON"
fi

# ── Servicio systemd ────────────────────────────────────────
echo "[1/2] Creando servicio systemd..."

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Autocount Gimnasio – Contador de personas IMX500
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${WORKDIR}
Environment=RELAY_URL=${RELAY_URL}
Environment=PI_TOKEN=${PI_TOKEN}
ExecStart=${PYTHON} ${WORKDIR}/${SCRIPT}
Restart=always
RestartSec=10
StartLimitIntervalSec=0

[Install]
WantedBy=multi-user.target
EOF

# ── Activar y arrancar ──────────────────────────────────────
echo "[2/2] Activando servicio..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

sleep 2
if [ "$(sudo systemctl is-active ${SERVICE_NAME})" = "active" ]; then
  echo "  ✓ Servicio activo"
else
  echo "  ✗ El servicio no arrancó. Revisa con:"
  echo "    sudo journalctl -u ${SERVICE_NAME} -n 30"
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Setup completado"
echo ""
echo "  En Vercel pon esta variable:"
echo "    VITE_WS_URL = ${RELAY_URL}"
echo ""
echo "  Comandos útiles:"
echo "    sudo systemctl status ${SERVICE_NAME}"
echo "    sudo journalctl -u ${SERVICE_NAME} -f"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
