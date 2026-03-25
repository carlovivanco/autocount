import asyncio
import csv
import cv2
import json
import math
import os
import threading
import time
from datetime import datetime

import websockets
from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

# -------------------------------------------------
# Configuración
# -------------------------------------------------
MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
THRESHOLD = 0.55
LINE_X = 320              # línea vertical de conteo
MAX_DISTANCE = 80         # distancia máxima para asociar detecciones
MAX_MISSES = 10           # frames que aguanta un track sin verse

# COCO: person = 0
PERSON_CLASS_ID = 0

# WebSocket
WS_PORT = 8765

# CSV de promedios horarios
CSV_FILE = "conteo_horario.csv"
SAMPLE_INTERVAL = 60      # segundos entre muestras para el promedio horario

# -------------------------------------------------
# Estado global
# -------------------------------------------------
last_detections = []
tracks = {}
next_id = 0
contador = 0

# -------------------------------------------------
# WebSocket
# -------------------------------------------------
ws_clients: set = set()
ws_loop: asyncio.AbstractEventLoop | None = None


async def _ws_handler(websocket):
    """Registra el cliente y envía el conteo actual al conectar."""
    ws_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"count": contador}))
        await websocket.wait_closed()
    finally:
        ws_clients.discard(websocket)


async def _broadcast(count: int):
    """Envía el conteo a todos los clientes conectados."""
    if not ws_clients:
        return
    msg = json.dumps({"count": count})
    await asyncio.gather(*[c.send(msg) for c in list(ws_clients)], return_exceptions=True)


def broadcast_count():
    """Llama a _broadcast desde el hilo principal sin bloquear."""
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
    """Toma una muestra por minuto y guarda el promedio al cambiar de hora."""
    global _last_sample_time, _last_hour, _hourly_samples

    now_ts = time.time()
    now_dt = datetime.fromtimestamp(now_ts)
    current_hour = now_dt.replace(minute=0, second=0, microsecond=0)

    # Muestra cada SAMPLE_INTERVAL segundos
    if now_ts - _last_sample_time >= SAMPLE_INTERVAL:
        _hourly_samples.append(contador)
        _last_sample_time = now_ts

    # Al cambiar de hora: escribir promedio de la hora anterior
    if current_hour != _last_hour:
        if _hourly_samples:
            avg = sum(_hourly_samples) / len(_hourly_samples)
            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow(
                    [_last_hour.strftime("%Y-%m-%d %H:%M"), round(avg, 2)]
                )
            print(
                f"[CSV] {_last_hour.strftime('%Y-%m-%d %H:%M')} → promedio: {avg:.2f} personas"
            )
        _hourly_samples.clear()
        _last_hour = current_hour


# -------------------------------------------------
# Detección
# -------------------------------------------------
class Detection:
    def __init__(self, coords, category, conf, metadata):
        self.category = int(category)
        self.conf = float(conf)
        self.box = imx500.convert_inference_coords(coords, metadata, picam2)


def parse_detections(metadata):
    global last_detections

    np_outputs = imx500.get_outputs(metadata, add_batch=True)
    if np_outputs is None:
        return last_detections

    boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]

    if intrinsics.bbox_normalization:
        _, input_h = imx500.get_input_size()
        boxes = boxes / input_h

    if intrinsics.bbox_order == "xy":
        boxes = boxes[:, [1, 0, 3, 2]]

    detections = []
    for box, score, category in zip(boxes, scores, classes):
        if float(score) < THRESHOLD:
            continue
        if int(category) != PERSON_CLASS_ID:
            continue
        detections.append(Detection(box, category, score, metadata))

    last_detections = detections
    return detections


def distancia(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def actualizar_tracks(detections):
    global tracks, next_id, contador

    dets = []
    for det in detections:
        x, y, w, h = det.box
        x, y, w, h = int(x), int(y), int(w), int(h)

        if w * h < 1500:
            continue

        cx = x + w // 2
        cy = y + h // 2

        dets.append({
            "x1": x, "y1": y,
            "x2": x + w, "y2": y + h,
            "cx": cx, "cy": cy,
            "conf": det.conf,
        })

    usados = set()
    ids_tracks = list(tracks.keys())

    for det in dets:
        mejor_id = None
        mejor_dist = 1e9

        for tid in ids_tracks:
            if tid in usados:
                continue
            d = distancia(det["cx"], det["cy"], tracks[tid]["cx"], tracks[tid]["cy"])
            if d < mejor_dist and d < MAX_DISTANCE:
                mejor_dist = d
                mejor_id = tid

        if mejor_id is not None:
            tr = tracks[mejor_id]
            tr["prev_cx"] = tr["cx"]
            tr["cx"] = det["cx"]
            tr["cy"] = det["cy"]
            tr["x1"] = det["x1"]
            tr["y1"] = det["y1"]
            tr["x2"] = det["x2"]
            tr["y2"] = det["y2"]
            tr["conf"] = det["conf"]
            tr["misses"] = 0
            usados.add(mejor_id)
        else:
            tracks[next_id] = {
                "cx": det["cx"], "cy": det["cy"],
                "prev_cx": det["cx"],
                "x1": det["x1"], "y1": det["y1"],
                "x2": det["x2"], "y2": det["y2"],
                "conf": det["conf"],
                "misses": 0,
                "counted": False,
            }
            usados.add(next_id)
            next_id += 1

    for tid in list(tracks.keys()):
        if tid not in usados:
            tracks[tid]["misses"] += 1
            if tracks[tid]["misses"] > MAX_MISSES:
                del tracks[tid]

    for tid, tr in tracks.items():
        prev_cx = tr["prev_cx"]
        cx = tr["cx"]

        # izquierda → derecha = salida (-1)
        if not tr["counted"] and prev_cx < LINE_X <= cx:
            contador -= 1
            tr["counted"] = True

        # derecha → izquierda = entrada (+1)
        elif not tr["counted"] and prev_cx > LINE_X >= cx:
            contador += 1
            tr["counted"] = True

        if abs(cx - LINE_X) > 100:
            tr["counted"] = False


def draw_overlay(request, stream="main"):
    with MappedArray(request, stream) as m:
        h, w = m.array.shape[:2]
        cv2.line(m.array, (LINE_X, 0), (LINE_X, h), (0, 0, 255), 2)

        cv2.putText(
            m.array,
            f"Contador: {contador}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 0, 0),
            2,
        )

        for tid, tr in tracks.items():
            x1, y1, x2, y2 = tr["x1"], tr["y1"], tr["x2"], tr["y2"]
            cx, cy = tr["cx"], tr["cy"]

            cv2.rectangle(m.array, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(m.array, (cx, cy), 5, (0, 255, 0), -1)
            cv2.putText(
                m.array,
                f"ID {tid}",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )


# -------------------------------------------------
# Inicio IMX500
# -------------------------------------------------
imx500 = IMX500(MODEL)
intrinsics = imx500.network_intrinsics

if not intrinsics:
    intrinsics = NetworkIntrinsics()
    intrinsics.task = "object detection"

intrinsics.task = "object detection"
intrinsics.update_with_defaults()

picam2 = Picamera2(imx500.camera_num)
config = picam2.create_preview_configuration(
    controls={"FrameRate": intrinsics.inference_rate},
    buffer_count=12
)

imx500.show_network_fw_progress_bar()
picam2.pre_callback = draw_overlay
picam2.start(config, show_preview=True)

if intrinsics.preserve_aspect_ratio:
    imx500.set_auto_aspect_ratio()

# Inicializar CSV y servidor WebSocket
_init_csv()
threading.Thread(target=_start_ws_server, daemon=True).start()

print("Presiona Ctrl+C para salir")

# -------------------------------------------------
# Bucle principal
# -------------------------------------------------
try:
    prev_contador = contador
    while True:
        metadata = picam2.capture_metadata()
        detections = parse_detections(metadata)
        actualizar_tracks(detections)

        # Emitir por WebSocket solo cuando el conteo cambia
        if contador != prev_contador:
            broadcast_count()
            prev_contador = contador

        # Registrar muestra horaria
        _record_sample()

        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
