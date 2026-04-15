import asyncio
import csv
import cv2
import json
import os
import threading
import time
from datetime import datetime

import websockets
from picamera2 import Picamera2
from ultralytics import YOLO

# -------------------------------------------------
# Configuración
# -------------------------------------------------
MODEL_PATH = "yolo26n.pt"        # se descarga automáticamente la primera vez
CONFIDENCE = 0.4                 # confianza mínima de detección
LINE_X = 320                     # posición horizontal de la línea de conteo (px)
LINE_RESET_DIST = 100            # distancia (px) para habilitar un nuevo cruce
FRAME_W, FRAME_H = 640, 480

WS_PORT = 8765
CSV_FILE = "conteo_horario.csv"
SAMPLE_INTERVAL = 60             # segundos entre muestras horarias

# -------------------------------------------------
# Estado global
# -------------------------------------------------
contador = 0
prev_cx: dict[int, int] = {}    # track_id -> cx del frame anterior
crossed: dict[int, bool] = {}   # track_id -> si ya cruzó (cooldown activo)

# -------------------------------------------------
# WebSocket
# -------------------------------------------------
ws_clients: set = set()
ws_loop: asyncio.AbstractEventLoop | None = None


async def _ws_handler(websocket):
    ws_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"count": contador}))
        await websocket.wait_closed()
    finally:
        ws_clients.discard(websocket)


async def _broadcast(count: int):
    if not ws_clients:
        return
    msg = json.dumps({"count": count})
    await asyncio.gather(
        *[c.send(msg) for c in list(ws_clients)],
        return_exceptions=True,
    )


def broadcast_count():
    if ws_loop and ws_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(contador), ws_loop)


def _start_ws_server():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)

    async def _serve():
        async with websockets.serve(_ws_handler, "0.0.0.0", WS_PORT):
            print(f"WebSocket escuchando en ws://0.0.0.0:{WS_PORT}")
            await asyncio.Future()  # run forever

    ws_loop.run_until_complete(_serve())


# -------------------------------------------------
# CSV – promedio horario
# -------------------------------------------------
_hourly_samples: list[int] = []
_last_sample_time: float = time.time()
_last_hour: datetime = datetime.now().replace(minute=0, second=0, microsecond=0)


def _init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["hora", "promedio_personas"])


def _record_sample():
    global _last_sample_time, _last_hour, _hourly_samples

    now_ts = time.time()
    now_dt = datetime.fromtimestamp(now_ts)
    current_hour = now_dt.replace(minute=0, second=0, microsecond=0)

    if now_ts - _last_sample_time >= SAMPLE_INTERVAL:
        _hourly_samples.append(contador)
        _last_sample_time = now_ts

    if current_hour != _last_hour:
        if _hourly_samples:
            avg = sum(_hourly_samples) / len(_hourly_samples)
            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow(
                    [_last_hour.strftime("%Y-%m-%d %H:%M"), round(avg, 2)]
                )
            print(
                f"[CSV] {_last_hour.strftime('%Y-%m-%d %H:%M')}"
                f" → promedio: {avg:.2f} personas"
            )
        _hourly_samples.clear()
        _last_hour = current_hour


# -------------------------------------------------
# Inicio – cámara, modelo, servicios
# -------------------------------------------------
model = YOLO(MODEL_PATH)

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (FRAME_W, FRAME_H), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(2)  # warm-up

_init_csv()
threading.Thread(target=_start_ws_server, daemon=True).start()

print("Presiona q para salir")

# -------------------------------------------------
# Bucle principal
# -------------------------------------------------
prev_contador = contador

try:
    while True:
        frame = picam2.capture_array()

        results = model.track(
            frame,
            classes=[0],      # 0 = persona (COCO)
            persist=True,
            conf=CONFIDENCE,
            verbose=False,
        )

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, tid in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                # Dibujar bounding box y centro
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                cv2.putText(
                    frame, f"ID {tid}",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2,
                )

                # Lógica de cruce de línea
                if tid in prev_cx:
                    px = prev_cx[tid]
                    already = crossed.get(tid, False)

                    if not already and px < LINE_X <= cx:
                        contador -= 1          # izquierda → derecha = salida
                        crossed[tid] = True

                    elif not already and px > LINE_X >= cx:
                        contador += 1          # derecha → izquierda = entrada
                        crossed[tid] = True

                    # Resetear cooldown cuando se aleja de la línea
                    if abs(cx - LINE_X) > LINE_RESET_DIST:
                        crossed[tid] = False

                prev_cx[tid] = cx

        # Limpiar estado de IDs que ya no están siendo trackeados
        active_ids = (
            set(results[0].boxes.id.cpu().numpy().astype(int))
            if results[0].boxes.id is not None
            else set()
        )
        for tid in list(prev_cx):
            if tid not in active_ids:
                del prev_cx[tid]
                crossed.pop(tid, None)

        # Dibujar línea y contador sobre el frame
        cv2.line(frame, (LINE_X, 0), (LINE_X, FRAME_H), (0, 0, 255), 2)
        cv2.putText(
            frame, f"Contador: {contador}",
            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2,
        )

        cv2.imshow("Conteo por cruce - Gym Tec EdoMex", frame)

        # Emitir por WebSocket si el conteo cambió
        if contador != prev_contador:
            broadcast_count()
            prev_contador = contador

        # Muestra para el promedio horario del CSV
        _record_sample()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    pass

finally:
    cv2.destroyAllWindows()
    picam2.stop()
