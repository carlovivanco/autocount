import asyncio
import base64
import cv2
import io
import json
import math
import os
import threading
import time
from datetime import datetime, timedelta

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

WS_PORT          = 8765
PARQUET_FILE     = "conteo_horario.parquet"
ML_MODEL_FILE    = "peak_model.joblib"
COUNTER_STATE    = "contador_state.json"
SAMPLE_INTERVAL  = 60
RETRAIN_DAYS     = 14

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _load_counter_state() -> int:
    """Restaura el contador del día actual al reiniciar el script."""
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
ws_clients: set = set()
ws_loop: asyncio.AbstractEventLoop | None = None


def _excel_bytes() -> bytes:
    if not os.path.exists(PARQUET_FILE):
        return b""

    df = pd.read_parquet(PARQUET_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Añadir predicción ML si el modelo existe
    if os.path.exists(ML_MODEL_FILE) and len(df) >= 24:
        clf = joblib.load(ML_MODEL_FILE)
        df["clasificacion"] = clf.predict(df[["hora", "dia_semana"]])
        df["clasificacion"] = df["clasificacion"].map({1: "Peak", 0: "Off-peak"})
    else:
        df["clasificacion"] = "—"

    # Límite inicio de semana actual (lunes 00:00)
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # ── Hoja 1: Semana actual — detalle por hora ──────────────────────────
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

    # ── Hoja 2: Semanas anteriores — promedio por día de semana ──────────
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

    # ── Hoja 3: Meses anteriores — promedio por día de semana ────────────
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


def _log_event(tipo: str):
    events = _load_today_events()
    events.append({"tipo": tipo, "timestamp": datetime.now().isoformat()})
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
        result = clf.predict([[now.hour, now.weekday()]])[0]
        return "Peak" if result == 1 else "Off-peak"
    except Exception:
        return None


async def _broadcast(count: int):
    if not ws_clients:
        return
    msg = json.dumps({"count": count, "peak_prediction": _current_peak_prediction()})
    await asyncio.gather(
        *[c.send(msg) for c in list(ws_clients)],
        return_exceptions=True,
    )


async def _ws_handler(websocket):
    global contador
    ws_clients.add(websocket)
    try:
        await websocket.send(json.dumps({
            "count": contador,
            "peak_prediction": _current_peak_prediction(),
            "today_events": _load_today_events(),
        }))
        async for raw in websocket:
            try:
                data = json.loads(raw)
                cmd = data.get("command", "")
                if cmd == "increment":
                    contador += 1
                    _log_event("entrada")
                    _save_counter_state()
                    await _broadcast(contador)
                elif cmd == "decrement":
                    contador -= 1
                    _log_event("salida")
                    _save_counter_state()
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


async def _broadcast_midnight_reset():
    if not ws_clients:
        return
    msg = json.dumps({"count": 0, "peak_prediction": None, "midnight_reset": True})
    await asyncio.gather(*[c.send(msg) for c in list(ws_clients)], return_exceptions=True)


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
    global _last_sample_time, _last_hour, _hourly_samples, contador, _last_date

    now_ts = time.time()
    now_dt = datetime.fromtimestamp(now_ts)
    current_hour = now_dt.replace(minute=0, second=0, microsecond=0)
    current_date = now_dt.strftime("%Y-%m-%d")

    if current_date != _last_date:
        contador = 0
        tracks.clear()
        _hourly_samples.clear()
        _last_date = current_date
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
            tr["prev_x1"] = tr["x1"]
            tr["prev_x2"] = tr["x2"]
            tr.update({k: det[k] for k in det})
            tr["cx"] = det["cx"]
            tr["misses"] = 0
            usados.add(mejor_id)
        else:
            tracks[next_id] = {**det, "prev_cx": None, "prev_x1": None, "prev_x2": None, "misses": 0, "counted": False}
            usados.add(next_id)
            next_id += 1

    for tid in list(tracks.keys()):
        if tid not in usados:
            tracks[tid]["misses"] += 1
            if tracks[tid]["misses"] > MAX_MISSES:
                del tracks[tid]

    for tid, tr in tracks.items():
        if tr["prev_x1"] is None:
            continue
        x1, x2 = tr["x1"], tr["x2"]
        px1, px2 = tr["prev_x1"], tr["prev_x2"]
        if x1 > LINE_X and not tr["counted"] and px1 <= LINE_X:
            contador += 1
            tr["counted"] = True
            _log_event("entrada")
        elif x2 < LINE_X and not tr["counted"] and px2 >= LINE_X and contador > 0:
            contador -= 1
            tr["counted"] = True
            _log_event("salida")
        if tr["counted"] and abs(tr["cx"] - LINE_X) > 80:
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
picam2.start(config, show_preview=False)
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
            _save_counter_state()
            prev_contador = contador

        _record_sample()
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
