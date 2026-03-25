# AutoCount - Gym Occupancy Monitor

Real-time gym occupancy tracking system using a Raspberry Pi with IMX500 AI camera. The Python backend detects and counts people crossing a line; the React frontend displays the live count and logs statistics.

## Architecture

```
Raspberry Pi (IMX500 camera)
  └── contador_cruce_imx500.py
        ├── AI person detection (MobileNetV2)
        ├── Line-crossing counter
        ├── WebSocket server (:8765)  ──→  Browser (React app)
        └── CSV hourly logger             src/app/pages/Dashboard.tsx
              conteo_horario.csv            └── useCounterWebSocket hook
```

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4 |
| UI       | shadcn/ui, Radix UI, Lucide icons   |
| Charts   | Recharts                            |
| Backend  | Python 3, picamera2, IMX500         |
| Protocol | WebSocket (port 8765)               |
| Storage  | CSV (`conteo_horario.csv`)          |

## Local Frontend Development

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production build
```

When no Raspberry Pi is connected the dashboard automatically falls back to a random-walk simulation so the UI is always demoable.

## Raspberry Pi Backend Setup

```bash
# Install Python deps (picamera2 is pre-installed on Pi OS)
pip install websockets

# Run the counter
python contador_cruce_imx500.py
```

The script starts a WebSocket server on `0.0.0.0:8765` and saves hourly averages to `conteo_horario.csv` in the working directory.

## Environment Variables

Create a `.env.local` file (never commit secrets):

```
VITE_WS_URL=ws://raspberrypi.local:8765
```

| Variable       | Default                          | Description                    |
|----------------|----------------------------------|--------------------------------|
| `VITE_WS_URL`  | `ws://raspberrypi.local:8765`   | WebSocket URL of the Pi backend |

## WebSocket Protocol

The backend sends JSON messages whenever the count changes, and also immediately on client connect:

```json
{ "count": 12 }
```

`count` is the net number of people currently inside (integer, can be negative if calibration drifts).

## CSV Output Format

`conteo_horario.csv` — one row per completed hour:

```
hora,promedio_personas
2024-01-15 08:00,23.5
2024-01-15 09:00,31.0
```

- **hora**: start of the hour (`YYYY-MM-DD HH:MM`)
- **promedio_personas**: average of samples taken every minute during that hour

## Key Files

| File | Purpose |
|------|---------|
| `contador_cruce_imx500.py` | Python AI backend — camera, counting, WebSocket, CSV |
| `conteo_horario.csv` | Auto-generated hourly average CSV |
| `src/app/pages/Dashboard.tsx` | Live monitoring page |
| `src/app/pages/DailyLog.tsx` | Entry/exit log page |
| `src/app/hooks/useCounterWebSocket.ts` | WebSocket → React state hook |
| `src/app/hooks/useGymData.ts` | Shared session entry/exit log |
| `src/app/components/Counter.tsx` | Big number counter display |
| `src/app/components/TrafficLight.tsx` | Capacity traffic-light indicator |
| `src/app/components/CameraFeed.tsx` | Camera feed placeholder |

## Backend Configuration (contador_cruce_imx500.py)

| Constant | Default | Description |
|----------|---------|-------------|
| `LINE_X` | 320 | Horizontal pixel position of the counting line |
| `THRESHOLD` | 0.55 | Minimum detection confidence |
| `MAX_DISTANCE` | 80 | Max pixels to associate a detection with an existing track |
| `MAX_MISSES` | 10 | Frames before a track is dropped |
| `WS_PORT` | 8765 | WebSocket server port |
| `SAMPLE_INTERVAL` | 60 s | How often to sample the count for CSV averaging |

## Capacity Logic

`MAX_CAPACITY` is set to **40** in `Dashboard.tsx`. Change it there to adjust the thresholds:

- Green traffic light: < 65 %
- Yellow: 65–90 %
- Red: 90–100 %
- Critical (alert banner): > 100 %

## Development Branch

Active branch: `claude/frontend-backend-counter-integration-Mvzyf`
