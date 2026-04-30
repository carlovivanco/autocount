#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Autocount Pi – setup.sh
#  Uso: bash setup.sh <SUBDOMINIO> <TOKEN> [SCRIPT]
#
#  SUBDOMINIO : tu subdominio de DuckDNS  (sin .duckdns.org)
#  TOKEN      : tu token de DuckDNS
#  SCRIPT     : archivo Python a ejecutar (default: contador_cruce_imx500.py)
#
#  Qué hace:
#    1. Instala el actualizador de DuckDNS + cron cada 5 min
#    2. Crea y activa un servicio systemd que arranca el contador
#       automáticamente al encender la Pi y lo reinicia si crashea
# ─────────────────────────────────────────────────────────────
set -e

SUBDOMAIN="${1:?Falta el subdominio DuckDNS. Uso: bash setup.sh SUBDOMINIO TOKEN}"
TOKEN="${2:?Falta el token DuckDNS.    Uso: bash setup.sh SUBDOMINIO TOKEN}"
SCRIPT="${3:-contador_cruce_imx500.py}"

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="$(whoami)"
PYTHON="$(command -v python3)"
SERVICE_NAME="autocount"
DUCKDNS_DIR="$HOME/duckdns"

echo ""
echo "▶ Configurando en: $WORKDIR"
echo "▶ Script:          $SCRIPT"
echo "▶ Usuario:         $RUN_USER"
echo "▶ DuckDNS:         ${SUBDOMAIN}.duckdns.org"
echo ""

# ── 1. DuckDNS ─────────────────────────────────────────────
echo "[1/4] Configurando DuckDNS..."
mkdir -p "$DUCKDNS_DIR"

cat > "$DUCKDNS_DIR/duck.sh" << EOF
#!/bin/bash
curl -s "https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&ip=" \\
     -o "$DUCKDNS_DIR/duck.log"
EOF
chmod +x "$DUCKDNS_DIR/duck.sh"

# Primera ejecución para verificar
"$DUCKDNS_DIR/duck.sh"
RESULT=$(cat "$DUCKDNS_DIR/duck.log")
if [ "$RESULT" != "OK" ]; then
  echo "✗ DuckDNS respondió: $RESULT"
  echo "  Verifica tu subdominio y token en https://www.duckdns.org"
  exit 1
fi
echo "  ✓ DuckDNS OK — ${SUBDOMAIN}.duckdns.org apunta a tu IP"

# ── 2. Cron job cada 5 minutos ──────────────────────────────
echo "[2/4] Configurando cron job..."
(crontab -l 2>/dev/null | grep -v "duck.sh"; \
 echo "*/5 * * * * $DUCKDNS_DIR/duck.sh >/dev/null 2>&1") | crontab -
echo "  ✓ Cron activo: IP se actualizará cada 5 minutos"

# ── 3. Servicio systemd ─────────────────────────────────────
echo "[3/4] Creando servicio systemd..."

# Detectar entorno virtual si existe
if [ -f "$WORKDIR/venv/bin/python3" ]; then
  PYTHON="$WORKDIR/venv/bin/python3"
  echo "  ✓ Usando virtualenv detectado: $PYTHON"
fi

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Autocount Gimnasio – Contador de personas IMX500
After=network-online.target
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

# ── 4. Habilitar y arrancar ─────────────────────────────────
echo "[4/4] Activando servicio..."
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
echo "  WebSocket accesible en:"
echo "    ws://${SUBDOMAIN}.duckdns.org:8765"
echo ""
echo "  Próximo paso en Vercel:"
echo "    VITE_WS_URL = ws://${SUBDOMAIN}.duckdns.org:8765"
echo ""
echo "  Comandos útiles:"
echo "    sudo systemctl status ${SERVICE_NAME}    # estado"
echo "    sudo systemctl restart ${SERVICE_NAME}   # reiniciar"
echo "    sudo journalctl -u ${SERVICE_NAME} -f    # logs en vivo"
echo "    cat ~/duckdns/duck.log                   # último update DNS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
