import asyncio
import base64
import cv2
import io
import json
import os
import threading
import time
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import websockets
from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics
from sklearn.ensemble import RandomForestClassifier

# -------------------------------------------------
# Configuración
# -------------------------------------------------
# Ruta al modelo .rpk generado por el flujo de entrenamiento:
#   1. python train.py           → best.pt  +  best_imx_model/packerOut.zip
#   2. imx500-package packerOut.zip          → network.rpk  (ejecutar en la Pi)
#   3. Actualiza MODEL con la ruta al .rpk resultante.
MODEL = "/home/pi/proyecto/autocount/runs/detect/runs/gym_tec_yolo11n/yolo11n_finetuned/weights/best_imx_model/rpk_out/network.rpk"   # <-- ACTUALIZA ESTA RUTA
SHOW = False
THRESHOLD        = 0.50
LINE_X           = 320
LINE_GAP         = 50
LINE_LEFT        = LINE_X - LINE_GAP
LINE_RIGHT       = LINE_X + LINE_GAP
# Tracker SORT-lite (Kalman cv2 + IoU greedy) + conteo confirmado por velocidad
IOU_MIN          = 0.3       # IoU mínimo para emparejar detección con track
MAX_MISSES       = 15        # frames sin verse antes de descartar un track
MIN_HITS         = 3         # frames consecutivos antes de confirmar un track
MIN_VX           = 0.5       # |vx| (px/frame) mínimo para validar el cruce
MIN_AREA         = 1500      # área mínima de caja (px²)
MAX_AREA         = 150_000   # área máxima (descarta detecciones gigantes erróneas)
PERSON_CLASS_ID  = 0

RELAY_URL       = os.getenv("RELAY_URL", "wss://autocount-relay.onrender.com")
PI_TOKEN        = os.getenv("PI_TOKEN",  "autocount-pi-secret")
PARQUET_FILE    = "conteo_horario.parquet"
ML_MODEL_FILE   = "peak_model.joblib"
COUNTER_STATE   = "contador_state.json"
SAMPLE_INTERVAL = 60
RETRAIN_DAYS    = 30

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _load_counter_state() -> int:
    try:
        with open(COUNTER_STATE) as f:
            data = json.load(f)
        if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
            return max(0, int(data.get("count", 0)))
    except Exception:
        pass
    return 0


def _save_counter_state():
    try:
        with open(COUNTER_STATE, "w") as f:
            json.dump({"count": contador, "date": datetime.now().strftime("%Y-%m-%d")}, f)
    except Exception:
        pass


# -------------------------------------------------
# Estado global
# -------------------------------------------------
last_detections = []
tracks = {}
next_id = 0
contador = _load_counter_state()
_last_date: str = datetime.now().strftime("%Y-%m-%d")

# -------------------------------------------------
# WebSocket
# -------------------------------------------------
ws_connection = None
ws_loop: asyncio.AbstractEventLoop | None = None


def _excel_bytes() -> bytes:
    if not os.path.exists(PARQUET_FILE):
        return b""

    df = pd.read_parquet(PARQUET_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if os.path.exists(ML_MODEL_FILE) and len(df) >= 24:
        clf = joblib.load(ML_MODEL_FILE)
        df["clasificacion"] = clf.predict(df[["hora", "dia_semana"]])
        df["clasificacion"] = df["clasificacion"].map({1: "Peak", 0: "Off-peak"})
    else:
        df["clasificacion"] = "—"

    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    cur = df[df["timestamp"] >= week_start].copy()
    cur["hora_str"] = cur["hora"].apply(lambda h: f"{h:02d}:00")
    sheet1 = cur[["timestamp", "dia_nombre", "hora_str", "promedio_personas", "clasificacion"]].rename(columns={
        "timestamp":         "Fecha/Hora",
        "dia_nombre":        "Día",
        "hora_str":          "Hora",
        "promedio_personas": "Personas (prom. hora)",
        "clasificacion":     "Clasificación",
    })

    past = df[df["timestamp"] < week_start].copy()

    if not past.empty:
        iso = past["timestamp"].dt.isocalendar()
        past["semana"] = iso.year.astype(str) + "-S" + iso.week.astype(str).str.zfill(2)
        sheet2 = (
            past.groupby(["semana", "dia_semana", "dia_nombre"])["promedio_personas"]
            .mean().round(2).reset_index()
            .sort_values(["semana", "dia_semana"])
            [["semana", "dia_nombre", "promedio_personas"]]
            .rename(columns={"semana": "Semana", "dia_nombre": "Día",
                              "promedio_personas": "Promedio personas"})
        )
    else:
        sheet2 = pd.DataFrame(columns=["Semana", "Día", "Promedio personas"])

    if not past.empty:
        past["mes"] = past["timestamp"].dt.strftime("%Y-%m")
        sheet3 = (
            past.groupby(["mes", "dia_semana", "dia_nombre"])["promedio_personas"]
            .mean().round(2).reset_index()
            .sort_values(["mes", "dia_semana"])
            [["mes", "dia_nombre", "promedio_personas"]]
            .rename(columns={"mes": "Mes", "dia_nombre": "Día",
                              "promedio_personas": "Promedio personas"})
        )
    else:
        sheet3 = pd.DataFrame(columns=["Mes", "Día", "Promedio personas"])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        sheet1.to_excel(writer, index=False, sheet_name="Semana Actual")
        sheet2.to_excel(writer, index=False, sheet_name="Semanas Anteriores")
        sheet3.to_excel(writer, index=False, sheet_name="Meses Anteriores")
    return buf.getvalue()


def _today_events_file() -> str:
    return f"eventos_{datetime.now().strftime('%Y-%m-%d')}.json"


def _load_today_events() -> list:
    path = _today_events_file()
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


_last_event: dict | None = None


def _log_event(tipo: str, fuente: str = "auto"):
    global _last_event
    event = {"tipo": tipo, "fuente": fuente, "timestamp": datetime.now().isoformat()}
    _last_event = event
    events = _load_today_events()
    events.append(event)
    try:
        with open(_today_events_file(), "w") as f:
            json.dump(events, f)
    except Exception:
        pass


def _current_peak_prediction() -> str | None:
    if not os.path.exists(ML_MODEL_FILE):
        return None
    try:
        clf = joblib.load(ML_MODEL_FILE)
        now = datetime.now()
        result = clf.predict(pd.DataFrame([[now.hour, now.weekday()]], columns=["hora", "dia_semana"]))[0]
        return "Peak" if result == 1 else "Off-peak"
    except Exception:
        return None


def _get_peak_schedule() -> dict | None:
    if not os.path.exists(ML_MODEL_FILE):
        return None
    try:
        clf = joblib.load(ML_MODEL_FILE)
        schedule = {}
        for dia_n, dia_nombre in enumerate(DIAS):
            peak_hours = [
                hora for hora in range(6, 22)
                if clf.predict(pd.DataFrame([[hora, dia_n]], columns=["hora", "dia_semana"]))[0] == 1
            ]
            schedule[dia_nombre] = peak_hours
        return schedule
    except Exception:
        return None


async def _broadcast(count: int):
    global ws_connection, _last_event
    if ws_connection is None:
        return
    try:
        payload = {"count": count, "peak_prediction": _current_peak_prediction()}
        if _last_event is not None:
            payload["last_event"] = _last_event
            _last_event = None
        await ws_connection.send(json.dumps(payload))
    except Exception:
        pass


async def _ws_client_loop():
    global ws_connection, contador
    url = f"{RELAY_URL}?token={PI_TOKEN}"
    while True:
        try:
            async with websockets.connect(url) as ws:
                ws_connection = ws
                print(f"[Relay] Conectado a {RELAY_URL}")
                await ws.send(json.dumps({
                    "count": contador,
                    "peak_prediction": _current_peak_prediction(),
                    "today_events": _load_today_events(),
                    "peak_schedule": _get_peak_schedule(),
                }))
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        cmd = data.get("command", "")
                        if cmd == "increment":
                            contador += 1
                            _log_event("entrada", "manual")
                            _save_counter_state()
                            await _broadcast(contador)
                        elif cmd == "decrement":
                            if contador > 0:
                                contador -= 1
                            _log_event("salida", "manual")
                            _save_counter_state()
                            await _broadcast(contador)
                        elif cmd == "download_excel":
                            xlsx = _excel_bytes()
                            if xlsx:
                                b64 = base64.b64encode(xlsx).decode()
                                await ws.send(json.dumps({
                                    "excel_b64": b64,
                                    "filename": "conteo_horario.xlsx",
                                }))
                            else:
                                await ws.send(json.dumps({"error": "Sin datos aún"}))
                    except Exception:
                        pass
        except Exception as e:
            ws_connection = None
            print(f"[Relay] Desconectado ({e}). Reconectando en 5s…")
            await asyncio.sleep(5)


def broadcast_count():
    if ws_loop and ws_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(contador), ws_loop)


async def _broadcast_midnight_reset():
    global ws_connection
    if ws_connection is None:
        return
    try:
        msg = json.dumps({"count": 0, "peak_prediction": None, "midnight_reset": True})
        await ws_connection.send(msg)
    except Exception:
        pass


def _start_ws_client():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    ws_loop.run_until_complete(_ws_client_loop())


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
    global _last_sample_time, _last_hour, _hourly_samples, contador, _last_date, next_id

    now_ts = time.time()
    now_dt = datetime.fromtimestamp(now_ts)
    current_hour = now_dt.replace(minute=0, second=0, microsecond=0)
    current_date = now_dt.strftime("%Y-%m-%d")

    if current_date != _last_date:
        contador = 0
        tracks.clear()
        _hourly_samples.clear()
        _last_date = current_date
        next_id = 0
        _save_counter_state()
        print(f"[Reset] Medianoche — contador reiniciado")
        if ws_loop and ws_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _broadcast_midnight_reset(), ws_loop
            )

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
        broadcast_count()


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


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union > 0 else 0.0


def _new_kalman(cx, cy):
    """Kalman 2D constante-velocidad: estado [cx, cy, vx, vy], medición [cx, cy]."""
    kf = cv2.KalmanFilter(4, 2)
    kf.transitionMatrix = np.array([
        [1, 0, 1, 0],
        [0, 1, 0, 1],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)
    kf.measurementMatrix = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
    ], dtype=np.float32)
    kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2
    kf.measurementNoiseCov = np.eye(2, dtype=np.float32)
    kf.errorCovPost = np.eye(4, dtype=np.float32)
    kf.statePost = np.array([[cx], [cy], [0], [0]], dtype=np.float32)
    return kf


def actualizar_tracks(detections):
    """SORT-lite: predicción Kalman + matching greedy por IoU + 3 zonas con confirmación."""
    global tracks, next_id, contador

    # Convertir detecciones IMX500 a dicts y filtrar ruido / cajas gigantes
    dets = []
    for det in detections:
        x, y, w, h = [int(v) for v in det.box]
        area = w * h
        if area < MIN_AREA or area > MAX_AREA:
            continue
        dets.append({"x1": x, "y1": y, "x2": x+w, "y2": y+h,
                     "cx": x+w//2, "cy": y+h//2, "conf": det.conf})

    # 1) Predecir todos los tracks
    predicted_boxes = {}
    for tid, tr in tracks.items():
        pred = tr["kf"].predict()
        pcx, pcy = float(pred[0]), float(pred[1])
        tr["cx"], tr["cy"] = int(pcx), int(pcy)
        w_, h_ = tr["w"], tr["h"]
        predicted_boxes[tid] = (int(pcx - w_/2), int(pcy - h_/2),
                                int(pcx + w_/2), int(pcy + h_/2))

    # 2) Matching greedy por IoU
    pairs = []
    for i, det in enumerate(dets):
        det_box = (det["x1"], det["y1"], det["x2"], det["y2"])
        for tid, pbox in predicted_boxes.items():
            v = _iou(det_box, pbox)
            if v >= IOU_MIN:
                pairs.append((v, i, tid))
    pairs.sort(key=lambda p: p[0], reverse=True)

    used_dets, used_tracks, matches = set(), set(), []
    for v, i, tid in pairs:
        if i in used_dets or tid in used_tracks:
            continue
        used_dets.add(i); used_tracks.add(tid)
        matches.append((i, tid))

    # 3) Emparejados: corregir Kalman, bbox, sumar hit
    for i, tid in matches:
        det = dets[i]
        tr = tracks[tid]
        tr["kf"].correct(np.array([[np.float32(det["cx"])], [np.float32(det["cy"])]]))
        tr["x1"], tr["y1"], tr["x2"], tr["y2"] = det["x1"], det["y1"], det["x2"], det["y2"]
        tr["cx"], tr["cy"] = det["cx"], det["cy"]
        tr["w"], tr["h"] = det["x2"] - det["x1"], det["y2"] - det["y1"]
        tr["vx"] = float(tr["kf"].statePost[2])
        tr["misses"] = 0
        tr["hits"] += 1
        if tr["hits"] >= MIN_HITS:
            tr["confirmed"] = True

    # 4) No emparejados: envejecer
    for tid, tr in tracks.items():
        if tid in used_tracks:
            continue
        tr["misses"] += 1
        tr["x1"] = tr["cx"] - tr["w"] // 2
        tr["y1"] = tr["cy"] - tr["h"] // 2
        tr["x2"] = tr["cx"] + tr["w"] // 2
        tr["y2"] = tr["cy"] + tr["h"] // 2
        tr["vx"] = float(tr["kf"].statePost[2])
    for tid in list(tracks.keys()):
        if tracks[tid]["misses"] > MAX_MISSES:
            del tracks[tid]

    # 5) Detecciones huérfanas: crear track nuevo
    for i, det in enumerate(dets):
        if i in used_dets:
            continue
        tracks[next_id] = {
            "kf": _new_kalman(det["cx"], det["cy"]),
            "x1": det["x1"], "y1": det["y1"], "x2": det["x2"], "y2": det["y2"],
            "cx": det["cx"], "cy": det["cy"],
            "w": det["x2"] - det["x1"], "h": det["y2"] - det["y1"],
            "hits": 1, "misses": 0,
            "confirmed": MIN_HITS <= 1,
            "last_outer": None, "via_middle": False,
            "vx": 0.0, "conf": det["conf"],
        }
        next_id += 1

    # 6) Conteo por 3 zonas — sólo en tracks confirmados, validando dirección
    for tid, tr in tracks.items():
        if not tr["confirmed"]:
            continue
        cx = tr["cx"]
        if cx < LINE_LEFT:
            zone = "L"
        elif cx > LINE_RIGHT:
            zone = "R"
        else:
            zone = "M"
        if zone == "M":
            if tr.get("last_outer") is not None:
                tr["via_middle"] = True
        elif zone == "L":
            if (tr.get("last_outer") == "R" and tr.get("via_middle")
                    and tr["vx"] < -MIN_VX):
                _log_event("salida")
                if contador > 0:
                    contador -= 1
            tr["last_outer"] = "L"
            tr["via_middle"] = False
        else:
            if (tr.get("last_outer") == "L" and tr.get("via_middle")
                    and tr["vx"] > MIN_VX):
                contador += 1
                _log_event("entrada")
            tr["last_outer"] = "R"
            tr["via_middle"] = False


def draw_overlay(request, stream="main"):
    with MappedArray(request, stream) as m:
        h, w = m.array.shape[:2]
        cv2.line(m.array, (LINE_LEFT,  0), (LINE_LEFT,  h), (0, 0, 255), 8)
        cv2.line(m.array, (LINE_RIGHT, 0), (LINE_RIGHT, h), (0, 0, 255), 8)
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
# Los modelos YOLO exportados al IMX500 emiten coordenadas normalizadas [0,1]
# en orden (y1,x1,y2,x2); forzamos ambos flags para la transformación correcta.
intrinsics.bbox_normalization = True
intrinsics.bbox_order = "xy"

picam2 = Picamera2(imx500.camera_num)
config = picam2.create_preview_configuration(
    controls={"FrameRate": intrinsics.inference_rate}, buffer_count=12
)
imx500.show_network_fw_progress_bar()
picam2.pre_callback = draw_overlay
picam2.start(config, show_preview=SHOW)
if intrinsics.preserve_aspect_ratio:
    imx500.set_auto_aspect_ratio()

threading.Thread(target=_start_ws_client, daemon=True).start()
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
            _save_counter_state()
            prev_contador = contador

        _record_sample()
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    picam2.stop()

#python train.py --export runs/gym_tec_yolo11n/yolo11n_finetuned/weights/best.pt
