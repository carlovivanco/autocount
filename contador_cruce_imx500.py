import asyncio
import base64
import cv2
import io
import json
import math
import os
import threading
import time
from datetime import datetime

import joblib
import pandas as pd
import websockets
from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics
from sklearn.ensemble import RandomForestClassifier

# -------------------------------------------------
# Configuración
# -------------------------------------------------
MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
THRESHOLD        = 0.55
LINE_X           = 320
MAX_DISTANCE     = 80
MAX_MISSES       = 10
PERSON_CLASS_ID  = 0

WS_PORT         = 8765
PARQUET_FILE    = "conteo_horario.parquet"
ML_MODEL_FILE   = "peak_model.joblib"
SAMPLE_INTERVAL = 60
RETRAIN_DAYS    = 30

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

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


def _excel_bytes() -> bytes:
    if not os.path.exists(PARQUET_FILE):
        return b""
    df = pd.read_parquet(PARQUET_FILE)
    if os.path.exists(ML_MODEL_FILE) and len(df) >= 24:
        model = joblib.load(ML_MODEL_FILE)
        df["prediccion"] = model.predict(df[["hora", "dia_semana"]])
        df["prediccion"] = df["prediccion"].map({1: "Peak", 0: "Off-peak"})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Conteo Horario")
    return buf.getvalue()


async def _broadcast(count: int):
    if not ws_clients:
        return
    msg = json.dumps({"count": count})
    await asyncio.gather(
        *[c.send(msg) for c in list(ws_clients)],
        return_exceptions=True,
    )


async def _ws_handler(websocket):
    global contador
    ws_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"count": contador}))
        async for raw in websocket:
            try:
                data = json.loads(raw)
                cmd = data.get("command", "")
                if cmd == "increment":
                    contador += 1
                    await _broadcast(contador)
                elif cmd == "decrement":
                    contador -= 1
                    await _broadcast(contador)
                elif cmd == "download_excel":
                    xlsx = _excel_bytes()
                    if xlsx:
                        b64 = base64.b64encode(xlsx).decode()
                        await websocket.send(json.dumps({
                            "excel_b64": b64,
                            "filename": "conteo_horario.xlsx",
                        }))
                    else:
                        await websocket.send(json.dumps({"error": "Sin datos aún"}))
            except Exception:
                pass
    finally:
        ws_clients.discard(websocket)


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
            await asyncio.Future()

    ws_loop.run_until_complete(_serve())


# -------------------------------------------------
# Parquet – registro horario
# -------------------------------------------------
_hourly_samples: list[int] = []
_last_sample_time: float = time.time()
_last_hour: datetime = datetime.now().replace(minute=0, second=0, microsecond=0)


def _append_parquet(row: dict):
    df_new = pd.DataFrame([row])
    if os.path.exists(PARQUET_FILE):
        df_existing = pd.read_parquet(PARQUET_FILE)
        df = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_parquet(PARQUET_FILE, index=False)


def _should_retrain() -> bool:
    if not os.path.exists(ML_MODEL_FILE):
        return True
    age = (time.time() - os.path.getmtime(ML_MODEL_FILE)) / 86400
    return age >= RETRAIN_DAYS


def _train_model():
    if not os.path.exists(PARQUET_FILE):
        return
    df = pd.read_parquet(PARQUET_FILE)
    if len(df) < 24:
        return
    threshold = df["promedio_personas"].quantile(0.70)
    df["es_peak"] = (df["promedio_personas"] >= threshold).astype(int)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(df[["hora", "dia_semana"]], df["es_peak"])
    joblib.dump(clf, ML_MODEL_FILE)
    print(f"[ML] Modelo reentrenado — {len(df)} muestras, threshold peak: {threshold:.1f} personas")


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
            row = {
                "timestamp":         _last_hour.strftime("%Y-%m-%d %H:%M"),
                "hora":              _last_hour.hour,
                "dia_semana":        _last_hour.weekday(),
                "dia_nombre":        DIAS[_last_hour.weekday()],
                "promedio_personas": round(avg, 2),
            }
            _append_parquet(row)
            print(
                f"[Parquet] {row['timestamp']} ({row['dia_nombre']}) "
                f"→ {avg:.2f} personas"
            )
            if _should_retrain():
                _train_model()
        _hourly_samples.clear()
        _last_hour = current_hour


# -------------------------------------------------
# Detección IMX500
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
        if float(score) < THRESHOLD or int(category) != PERSON_CLASS_ID:
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
        x, y, w, h = [int(v) for v in det.box]
        if w * h < 1500:
            continue
        dets.append({"x1": x, "y1": y, "x2": x+w, "y2": y+h,
                     "cx": x+w//2, "cy": y+h//2, "conf": det.conf})

    usados = set()
    ids_tracks = list(tracks.keys())
    for det in dets:
        mejor_id, mejor_dist = None, 1e9
        for tid in ids_tracks:
            if tid in usados:
                continue
            d = distancia(det["cx"], det["cy"], tracks[tid]["cx"], tracks[tid]["cy"])
            if d < mejor_dist and d < MAX_DISTANCE:
                mejor_dist, mejor_id = d, tid
        if mejor_id is not None:
            tr = tracks[mejor_id]
            tr["prev_cx"] = tr["cx"]
            tr.update({k: det[k] for k in det})
            tr["cx"] = det["cx"]
            tr["misses"] = 0
            usados.add(mejor_id)
        else:
            tracks[next_id] = {**det, "prev_cx": det["cx"], "misses": 0, "counted": False}
            usados.add(next_id)
            next_id += 1

    for tid in list(tracks.keys()):
        if tid not in usados:
            tracks[tid]["misses"] += 1
            if tracks[tid]["misses"] > MAX_MISSES:
                del tracks[tid]

    for tid, tr in tracks.items():
        px, cx = tr["prev_cx"], tr["cx"]
        if not tr["counted"] and px < LINE_X <= cx:
            contador += 1
            tr["counted"] = True
        elif not tr["counted"] and px > LINE_X >= cx and contador > 0:
            contador -= 1
            tr["counted"] = True
        if abs(cx - LINE_X) > 100:
            tr["counted"] = False


def draw_overlay(request, stream="main"):
    with MappedArray(request, stream) as m:
        h, w = m.array.shape[:2]
        cv2.line(m.array, (LINE_X, 0), (LINE_X, h), (0, 0, 255), 12)
        cv2.putText(m.array, f"Contador: {contador}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
        for tid, tr in tracks.items():
            cv2.rectangle(m.array, (tr["x1"], tr["y1"]), (tr["x2"], tr["y2"]), (0, 255, 0), 2)
            cv2.circle(m.array, (tr["cx"], tr["cy"]), 5, (0, 255, 0), -1)
            cv2.putText(m.array, f"ID {tid}", (tr["x1"], max(20, tr["y1"]-8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)


# -------------------------------------------------
# Inicio IMX500
# -------------------------------------------------
imx500 = IMX500(MODEL)
intrinsics = imx500.network_intrinsics or NetworkIntrinsics()
intrinsics.task = "object detection"
intrinsics.update_with_defaults()

picam2 = Picamera2(imx500.camera_num)
config = picam2.create_preview_configuration(
    controls={"FrameRate": intrinsics.inference_rate}, buffer_count=12
)
imx500.show_network_fw_progress_bar()
picam2.pre_callback = draw_overlay
picam2.start(config, show_preview=True)
if intrinsics.preserve_aspect_ratio:
    imx500.set_auto_aspect_ratio()

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

        if contador != prev_contador:
            broadcast_count()
            prev_contador = contador

        _record_sample()
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
