# AutoCount — Gimnasio Tec de Monterrey Campus Estado de México

Sistema de monitoreo de aforo en tiempo real usando una Raspberry Pi con cámara IMX500 o webcam USB, YOLO26n, y un dashboard web desplegado en Vercel.

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Requisitos](#requisitos)
3. [Raspberry Pi — Backend](#raspberry-pi--backend)
4. [Frontend — Desarrollo local](#frontend--desarrollo-local)
5. [Despliegue en Vercel](#despliegue-en-vercel)
6. [Exponer el Pi a internet (Cloudflare Tunnel)](#exponer-el-pi-a-internet-cloudflare-tunnel)
7. [Arranque automático](#arranque-automático)
8. [Panel de administración](#panel-de-administración)
9. [Entrenamiento del modelo YOLO](#entrenamiento-del-modelo-yolo)
10. [Datos y modelo ML de peak hours](#datos-y-modelo-ml-de-peak-hours)
11. [Variables de entorno](#variables-de-entorno)
12. [Scripts disponibles](#scripts-disponibles)
13. [Flujo de desarrollo (git)](#flujo-de-desarrollo-git)

---

## Arquitectura

```
Raspberry Pi (cámara IMX500 o webcam)
  └── contador_cruce.py  /  contador_cruce_imx500.py
        ├── YOLO26n / MobileNetV2 — detección de personas
        ├── Lógica de cruce de línea — conteo entrada/salida
        ├── WebSocket server (puerto 8765) ──────────────────────┐
        └── Parquet horario + modelo ML peak/off-peak            │
                                                                  ↓
                                              Browser (Vercel)
                                              src/app/pages/Dashboard.tsx
                                              src/app/pages/AdminPanel.tsx
                                              src/app/hooks/useCounterWebSocket.ts
```

---

## Requisitos

### Raspberry Pi
- Raspberry Pi 4 / 5 con Raspberry Pi OS (64-bit recomendado)
- Cámara IMX500 **o** webcam USB
- Python 3.10+
- Conexión a internet para el túnel

### Máquina de desarrollo
- Node.js 18+
- npm 9+
- Git

---

## Raspberry Pi — Backend

### 1. Clonar el repositorio

```bash
git clone https://github.com/carlovivanco/autocount.git
cd autocount
```

### 2. Instalar dependencias Python

```bash
pip install websockets pandas pyarrow scikit-learn joblib openpyxl ultralytics
# picamera2 ya viene preinstalado en Raspberry Pi OS
```

### 3. Elegir y correr el script según tu cámara

**Con cámara IMX500 (aceleración por hardware):**
```bash
python contador_cruce_imx500.py
```

**Con webcam USB o cámara estándar del Pi (usa YOLO26n):**
```bash
python contador_cruce.py
```

Ambos scripts inician el servidor WebSocket en `ws://0.0.0.0:8765` y muestran en consola:
```
WebSocket escuchando en ws://0.0.0.0:8765
Presiona q para salir
```

### 4. Controles en pantalla
| Tecla | Acción |
|-------|--------|
| `q`   | Salir  |

---

## Frontend — Desarrollo local

```bash
# Instalar dependencias
npm install

# Crear archivo de entorno local
cp .env.example .env.local
# Editar .env.local con la URL de tu Pi local:
# VITE_WS_URL=ws://raspberrypi.local:8765

# Iniciar servidor de desarrollo
npm run dev
# → http://localhost:5173

# Build de producción
npm run build
```

---

## Despliegue en Vercel

### 1. Conectar repositorio
1. Entra a [vercel.com](https://vercel.com) y crea una cuenta con GitHub
2. **Add New Project** → importa `carlovivanco/autocount`
3. **Framework Preset: Vite** (Vercel lo detecta automáticamente)
4. Click en **Deploy**

### 2. Agregar variables de entorno
En **Settings → Environment Variables** agrega:

| Variable | Valor | Descripción |
|---|---|---|
| `VITE_WS_URL` | `wss://tu-tunnel.trycloudflare.com` | URL del túnel Cloudflare (ver sección siguiente) |
| `VITE_ADMIN_USER` | `tu_usuario` | Usuario del panel admin |
| `VITE_ADMIN_PASSWORD` | `tu_contraseña` | Contraseña del panel admin |

### 3. Redeplegar
Después de agregar las variables ve a **Deployments → Redeploy** para que el build las incluya.

---

## Exponer el Pi a internet (Cloudflare Tunnel)

El frontend en Vercel (HTTPS) requiere `wss://` — no puede conectarse a `ws://` directamente. Cloudflare Tunnel resuelve esto de forma gratuita.

### Instalación (una sola vez)

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 \
  -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/
```

### Uso básico (URL temporal, cambia al reiniciar)

```bash
cloudflared tunnel --url ws://localhost:8765
# Imprime algo como: https://algo-random.trycloudflare.com
# Copia esa URL y úsala en Vercel como wss://algo-random.trycloudflare.com
```

### URL fija (requiere dominio propio)

```bash
# Autenticarse con tu cuenta de Cloudflare
cloudflared login

# Crear túnel con nombre permanente
cloudflared tunnel create gym-tec

# Configurar (~/.cloudflared/config.yml)
cat > ~/.cloudflared/config.yml << EOF
tunnel: gym-tec
credentials-file: /home/pi/.cloudflared/<UUID>.json
ingress:
  - service: ws://localhost:8765
EOF

# Asignar subdominio (necesitas un dominio en Cloudflare)
cloudflared tunnel route dns gym-tec gym-tec.tudominio.com
```

---

## Arranque automático

Para que el Pi inicie todo solo al encenderse y se recupere automáticamente si algo falla:

### 1. Configurar el script de arranque

Edita `scripts/arrancar.sh` y rellena las 4 variables al inicio del archivo:

```bash
VERCEL_TOKEN="..."       # vercel.com/account/tokens → Create Token
PROJECT_ID="..."         # vercel.com/<proyecto>/settings → Project ID
ENV_VAR_ID="..."         # Ver instrucción abajo
DEPLOY_HOOK="..."        # vercel.com/<proyecto>/settings/git → Deploy Hooks
```

**Para obtener `ENV_VAR_ID`:**
```bash
curl -H "Authorization: Bearer <TU_TOKEN>" \
  "https://api.vercel.com/v9/projects/<PROJECT_ID>/env" | python3 -m json.tool \
  | grep -A2 "VITE_WS_URL"
# Copia el valor del campo "id"
```

### 2. Instalar el servicio systemd

```bash
chmod +x scripts/arrancar.sh
sudo cp scripts/gym-tec.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gym-tec
sudo systemctl start gym-tec
```

### 3. Comandos útiles

```bash
sudo systemctl status gym-tec        # Ver estado
sudo journalctl -u gym-tec -f        # Ver logs en vivo
sudo systemctl restart gym-tec       # Reiniciar manualmente
sudo systemctl stop gym-tec          # Detener
```

### Qué hace automáticamente
1. Inicia Cloudflare Tunnel y captura la nueva URL
2. Actualiza `VITE_WS_URL` en Vercel vía API
3. Dispara un redeploy de Vercel (~1 min)
4. Arranca el backend Python
5. Si algo falla, systemd reinicia todo en 15 segundos

---

## Panel de administración

Accede en: `https://tu-app.vercel.app/admin`

| Función | Descripción |
|---|---|
| **Login** | Usuario y contraseña configurados en Vercel (`VITE_ADMIN_USER` / `VITE_ADMIN_PASSWORD`) |
| **+1 Entrada** | Suma 1 al contador manualmente (si la cámara no detectó) |
| **−1 Salida** | Resta 1 al contador manualmente |
| **Descargar Excel** | Descarga el historial horario en `.xlsx` con columna de predicción peak/off-peak |

La sesión se mantiene mientras el tab esté abierto y se cierra al cerrar el navegador.

---

## Entrenamiento del modelo YOLO

Si quieres afinar el modelo para mejorar la detección en las condiciones específicas del gym (iluminación, ángulo de cámara):

### 1. Etiquetar fotos con Roboflow

1. Sube fotos del gym en [roboflow.com](https://roboflow.com)
2. Dibuja bounding boxes alrededor de cada persona
3. Exporta en formato **YOLOv8** — descarga la carpeta `dataset/`

### 2. Estructura esperada

```
dataset/
├── images/
│   ├── train/     (80% de las fotos)
│   └── val/       (20% de las fotos)
├── labels/
│   ├── train/
│   └── val/
└── data.yaml
```

### 3. Entrenar

```bash
# Instalar dependencia adicional
pip install ultralytics

# Correr fine-tuning (en tu laptop/PC, no en el Pi)
python train.py
```

El mejor modelo se guarda en `runs/gym_tec/yolo26n_finetuned/weights/best.pt`.

### 4. Usar el modelo afinado

En `contador_cruce.py` cambia:
```python
MODEL_PATH = "runs/gym_tec/yolo26n_finetuned/weights/best.pt"
```

### Detección pura sin contador (para pruebas)

```bash
python detectar_personas.py
# Muestra bounding boxes y porcentaje de confianza sin ningún otro proceso
```

---

## Datos y modelo ML de peak hours

### Formato del archivo Parquet

`conteo_horario.parquet` — se genera automáticamente, una fila por hora completada:

| Campo | Tipo | Descripción |
|---|---|---|
| `timestamp` | string | Inicio de la hora (`YYYY-MM-DD HH:MM`) |
| `hora` | int | Hora del día (0–23) |
| `dia_semana` | int | Día de la semana (0 = Lunes, 6 = Domingo) |
| `dia_nombre` | string | Nombre del día en español |
| `promedio_personas` | float | Promedio de personas durante esa hora |

### Modelo de clasificación

- **Algoritmo:** RandomForestClassifier (scikit-learn)
- **Features:** `hora`, `dia_semana`
- **Target:** `es_peak` — 1 si `promedio_personas >= percentil 70`, 0 si no
- **Reentrenamiento:** automático cada 30 días si hay ≥ 24 muestras
- **Modelo guardado en:** `peak_model.joblib`

### Excel exportado desde el admin

El archivo descargado incluye todas las columnas del Parquet más:

| Campo | Descripción |
|---|---|
| `prediccion` | "Peak" u "Off-peak" según el modelo ML |

---

## Variables de entorno

### Frontend (Vercel)

| Variable | Ejemplo | Descripción |
|---|---|---|
| `VITE_WS_URL` | `wss://abc.trycloudflare.com` | URL WebSocket del Pi |
| `VITE_ADMIN_USER` | `admin` | Usuario del panel admin |
| `VITE_ADMIN_PASSWORD` | `clave_segura` | Contraseña del panel admin |

Crea `.env.local` para desarrollo local (nunca lo subas al repo):
```bash
cp .env.example .env.local
```

### Backend (Pi) — configurables al inicio de cada script

| Constante | Default | Descripción |
|---|---|---|
| `LINE_X` | `320` | Posición de la línea de conteo (px) |
| `CONFIDENCE` | `0.4` | Confianza mínima YOLO |
| `WS_PORT` | `8765` | Puerto WebSocket |
| `SAMPLE_INTERVAL` | `60` | Segundos entre muestras horarias |
| `RETRAIN_DAYS` | `30` | Días entre reentrenamientos del modelo ML |

---

## Scripts disponibles

| Script | Descripción |
|---|---|
| `contador_cruce.py` | Backend principal — YOLO26n + webcam/cámara Pi |
| `contador_cruce_imx500.py` | Backend alternativo — MobileNetV2 + cámara IMX500 |
| `detectar_personas.py` | Detección pura sin contador (pruebas) |
| `train.py` | Fine-tuning de YOLO26n con fotos del gym |
| `scripts/arrancar.sh` | Arranque automático + actualización de Vercel |
| `scripts/gym-tec.service` | Servicio systemd para el Pi |

---

## Flujo de desarrollo (git)

```bash
# Clonar
git clone https://github.com/carlovivanco/autocount.git
cd autocount

# Crear rama para tus cambios
git checkout -b mi-feature

# Hacer cambios, luego...
git add .
git commit -m "Descripción clara del cambio"
git push origin mi-feature

# Abrir Pull Request en GitHub hacia main
```

Vercel hace deploy automático de cada push a `main`.
