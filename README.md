# AutoCount — Gimnasio Tec de Monterrey Campus Estado de México

Sistema de monitoreo de aforo en tiempo real usando una Raspberry Pi con cámara IMX500, YOLO11n, y un dashboard web desplegado en Vercel.

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Requisitos](#requisitos)
3. [Relay Server — Render](#relay-server--render)
4. [Raspberry Pi — Backend](#raspberry-pi--backend)
5. [Frontend — Desarrollo local](#frontend--desarrollo-local)
6. [Despliegue en Vercel](#despliegue-en-vercel)
7. [Arranque automático (plug-and-play)](#arranque-automático-plug-and-play)
8. [Panel de administración](#panel-de-administración)
9. [Entrenamiento del modelo YOLO](#entrenamiento-del-modelo-yolo)
10. [Datos y modelo ML de peak hours](#datos-y-modelo-ml-de-peak-hours)
11. [Variables de entorno](#variables-de-entorno)
12. [Scripts disponibles](#scripts-disponibles)
13. [Flujo de desarrollo (git)](#flujo-de-desarrollo-git)

---

## Arquitectura

```
Raspberry Pi (cámara IMX500)
  └── contador_cruce_imx500_trained.py
        ├── YOLO11n — detección de personas
        ├── Lógica de cruce de línea — conteo entrada/salida
        ├── Parquet horario + modelo ML peak/off-peak
        └── WebSocket client ──────────────────────────────┐
                                                           ↓
                                          Relay Server (Render)
                                          relay/server.js
                                          wss://autocount-relay.onrender.com
                                                           │
                                                           ↓
                                              Browser (Vercel)
                                              src/app/pages/Dashboard.tsx
                                              src/app/pages/AdminPanel.tsx
                                              src/app/hooks/useCounterWebSocket.ts
```

**Por qué relay:** La red del campus bloquea conexiones entrantes, por lo que la Pi no puede exponer un servidor. En cambio, la Pi se conecta como *cliente* al relay en Render (salida permitida), y el frontend también se conecta al mismo relay. El relay reenvía mensajes en ambas direcciones. La URL del relay es permanente — no cambia nunca.

---

## Requisitos

### Raspberry Pi
- Raspberry Pi 4 / 5 con Raspberry Pi OS (64-bit recomendado)
- Cámara IMX500
- Python 3.10+
- Virtualenv `yolo-env` con dependencias instaladas

### Máquina de desarrollo
- Node.js 18+
- npm 9+
- Git

---

## Relay Server — Render

El relay es un servidor Node.js desplegado en [render.com](https://render.com) (plan gratuito). Ya está desplegado en `wss://autocount-relay.onrender.com`.

### Desplegar tu propio relay (opcional)

1. Crea una cuenta en [render.com](https://render.com)
2. **New → Web Service** → conecta el repositorio `carlovivanco/autocount`
3. Configura:
   - **Root Directory:** `relay`
   - **Build Command:** `npm install`
   - **Start Command:** `npm start`
4. Agrega variables de entorno:

   | Variable | Descripción |
   |---|---|
   | `PI_TOKEN` | Token secreto compartido con la Pi (ej. `autocount-pi-secret`) |

5. Despliega — Render te da una URL permanente del tipo `https://tu-relay.onrender.com`

> **Nota:** El plan gratuito de Render "hiberna" servicios sin tráfico. La conexión persistente de la Pi evita que el relay hiberne mientras esté encendida.

---

## Raspberry Pi — Backend

### 1. Clonar el repositorio

```bash
git clone https://github.com/carlovivanco/autocount.git
cd autocount
```

### 2. Instalar dependencias Python

```bash
python3 -m venv yolo-env
source yolo-env/bin/activate
pip install websockets pandas pyarrow scikit-learn joblib openpyxl ultralytics
# picamera2 ya viene preinstalado en Raspberry Pi OS
```

### 3. Correr el script manualmente

```bash
source yolo-env/bin/activate
RELAY_URL=wss://autocount-relay.onrender.com \
PI_TOKEN=autocount-pi-secret \
python3 contador_cruce_imx500_trained.py
```

La consola mostrará:
```
[Relay] Conectado a wss://autocount-relay.onrender.com
```

### 4. Controles en pantalla
| Tecla | Acción |
|-------|--------|
| `q`   | Salir  |

---

## Alternativa: cámara normal + AI HAT+ (Hailo)

`contador_cruce.py` es la variante para una **cámara normal** (USB/CSI, no la IMX500) que
corre el modelo **YOLO11s afinado** en el **AI HAT+ (acelerador Hailo)** mediante
`picamera2.devices.Hailo`. El conteo, el WebSocket local, el Parquet y el modelo ML son los
mismos que las demás variantes; solo cambia el backend de inferencia.

### 1. Instalar el stack Hailo en la Pi
```bash
sudo apt update && sudo apt install hailo-all   # HailoRT + soporte Hailo de picamera2
hailortcli scan                                  # debe listar el dispositivo del AI HAT+
```

### 2. Compilar el modelo a .hef (en PC x86, no en la Pi)
El AI HAT+ corre modelos en formato `.hef` compilado, no archivos `.pt`. Usa el script de
conversión `best.pt → ONNX → .hef` dentro del Hailo AI Software Suite / Model Zoo:
```bash
# 13 TOPS (AI HAT+ / AI Kit):
HW_ARCH=hailo8l bash scripts/export_to_hailo.sh
# 26 TOPS:
HW_ARCH=hailo8  bash scripts/export_to_hailo.sh
```
Genera `models/yolo11s_gym.hef`. Cópialo a la Pi en `autocount/models/`. (El runtime HailoRT
autodetecta el HAT; el `.hef` debe estar compilado para el arch correcto: `hailo8` o `hailo8l`.)

### 3. Correr
```bash
# Con pantalla (cajas, líneas y contador en una ventana):
SHOW=1 HEF_MODEL=models/yolo11s_gym.hef python3 contador_cruce.py
# Headless (servicio, sin ventana):
HEF_MODEL=models/yolo11s_gym.hef python3 contador_cruce.py
```

| Variable | Default | Descripción |
|---|---|---|
| `HEF_MODEL` | `models/yolo11s_gym.hef` | Ruta al `.hef` compilado |
| `SHOW` | `0` | `1` abre la ventana `cv2.imshow` (tecla `q` para salir); `0` = headless |

Para arranque automático puedes reutilizar el servidor systemd pasando este script:
`bash pi-setup/setup.sh <RELAY_URL> <PI_TOKEN> contador_cruce.py` (esta variante usa un
servidor WebSocket **local** en `ws://0.0.0.0:8765`, así que los argumentos de relay se ignoran).

---

## Frontend — Desarrollo local

```bash
# Instalar dependencias
npm install

# Crear archivo de entorno local
cp .env.example .env.local
# Editar .env.local:
# VITE_WS_URL=wss://autocount-relay.onrender.com

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
| `VITE_WS_URL` | `wss://autocount-relay.onrender.com` | URL del relay (permanente, no cambia) |
| `VITE_ADMIN_USER` | `tu_usuario` | Usuario del panel admin |
| `VITE_ADMIN_PASSWORD` | `tu_contraseña` | Contraseña del panel admin |

### 3. Redeplegar
Después de agregar las variables ve a **Deployments → Redeploy**.

---

## Arranque automático (plug-and-play)

El script `pi-setup/setup.sh` configura un servicio systemd para que el contador arranque solo al encender la Pi y se reconecte automáticamente si pierde la red.

### Instalación (una sola vez)

```bash
bash pi-setup/setup.sh <RELAY_URL> <PI_TOKEN>
```

**Ejemplo:**
```bash
bash pi-setup/setup.sh wss://autocount-relay.onrender.com autocount-pi-secret
```

El script:
1. Crea `/etc/systemd/system/autocount.service`
2. Habilita el servicio para que inicie al encender
3. Lo inicia inmediatamente

### Comandos útiles

```bash
sudo systemctl status autocount        # Ver estado
sudo journalctl -u autocount -f        # Ver logs en vivo
sudo systemctl restart autocount       # Reiniciar manualmente
sudo systemctl stop autocount          # Detener
```

### Flujo tras un reinicio de la Pi

1. Pi enciende → systemd inicia `autocount.service`
2. Script se conecta como cliente WebSocket al relay en Render
3. Envía estado inicial (`count`, `peak_prediction`, `peak_schedule`, `today_events`)
4. Relay notifica a todos los frontends que la Pi está conectada
5. Dashboard actualiza el contador y muestra el indicador "● Raspberry Pi conectada"

---

## Panel de administración

Accede en: `https://tu-app.vercel.app/admin`

| Función | Descripción |
|---|---|
| **Login** | Usuario y contraseña configurados en Vercel (`VITE_ADMIN_USER` / `VITE_ADMIN_PASSWORD`) |
| **+1 Entrada** | Suma 1 al contador manualmente |
| **−1 Salida** | Resta 1 al contador manualmente |
| **Descargar Excel** | Descarga el historial horario en `.xlsx` con columna de predicción peak/off-peak |

La sesión se mantiene mientras el tab esté abierto y se cierra al cerrar el navegador.

---

## Entrenamiento del modelo YOLO

Si quieres afinar el modelo para mejorar la detección en las condiciones del gym:

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

### 3. Entrenar (en laptop/PC, no en la Pi)

```bash
pip install ultralytics
python train.py
```

El mejor modelo se guarda en `runs/gym_tec_yolo11n/yolo11n_finetuned/weights/best.pt`.

### 4. Empaquetar para IMX500 (en la Pi)

```bash
imx500-package best_imx_model/packerOut.zip
# genera network.rpk
```

Actualiza la constante `MODEL` en `contador_cruce_imx500_trained.py` con la ruta al `.rpk`.

---

## Datos y modelo ML de peak hours

### Cómo funciona

El script registra automáticamente el promedio de personas por hora en `conteo_horario.parquet`. Cada 30 días (o manualmente) se reentrena un RandomForestClassifier que predice si cada hora de cada día es "Peak" u "Off-peak".

Los horarios predichos aparecen en el dashboard bajo **"Horarios Peak · Predicción IA"**.

### Entrenar manualmente

```bash
cd /ruta/a/autocount
python3 - <<'EOF'
import pandas as pd, joblib, numpy as np
from sklearn.ensemble import RandomForestClassifier

df = pd.read_parquet("conteo_horario.parquet")
threshold = df["promedio_personas"].quantile(0.70)
df["es_peak"] = (df["promedio_personas"] >= threshold).astype(int)
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(df[["hora", "dia_semana"]], df["es_peak"])
joblib.dump(clf, "peak_model.joblib")
print(f"Modelo entrenado. Umbral peak: {threshold:.1f} personas/hora")
EOF
sudo systemctl restart autocount
```

### Formato del archivo Parquet

`conteo_horario.parquet` — una fila por hora completada:

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

---

## Variables de entorno

### Frontend (Vercel / `.env.local`)

| Variable | Ejemplo | Descripción |
|---|---|---|
| `VITE_WS_URL` | `wss://autocount-relay.onrender.com` | URL del relay WebSocket |
| `VITE_ADMIN_USER` | `admin` | Usuario del panel admin |
| `VITE_ADMIN_PASSWORD` | `clave_segura` | Contraseña del panel admin |

### Backend (Pi) — variables de entorno del servicio systemd

| Variable | Default | Descripción |
|---|---|---|
| `RELAY_URL` | `wss://autocount-relay.onrender.com` | URL del relay |
| `PI_TOKEN` | `autocount-pi-secret` | Token de autenticación con el relay |

### Relay (Render)

| Variable | Descripción |
|---|---|
| `PI_TOKEN` | Debe coincidir con el token configurado en la Pi |
| `PORT` | Puerto (Render lo asigna automáticamente) |

---

## Scripts disponibles

| Script | Descripción |
|---|---|
| `contador_cruce_imx500_trained.py` | Backend principal — YOLO11n + IMX500, cliente WebSocket del relay |
| `contador_cruce.py` | Backend cámara normal + AI HAT+ (Hailo) — YOLO11s, servidor WebSocket local |
| `scripts/export_to_hailo.sh` | Compila el YOLO11s afinado a `.hef` (best.pt → ONNX → .hef) |
| `train.py` | Fine-tuning de YOLO11n con fotos del gym |
| `pi-setup/setup.sh` | Instala y configura el servicio systemd en la Pi |
| `relay/server.js` | Relay WebSocket desplegado en Render |

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
