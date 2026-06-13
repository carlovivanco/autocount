"""
Contador de cruce con cámara IMX500 — versión STANDALONE.

Igual que contador_cruce_imx500_trained.py pero sin WebSocket, sin parquet,
sin modelo ML de predicción de peaks. Sólo:
  - Carga el modelo .rpk en la cámara IMX500.
  - Detecta personas con el modelo entrenado.
  - Trackea cruces izquierda<->derecha sobre la línea central.
  - Mantiene un contador en pantalla y lo persiste en disco.

Variables de entorno opcionales:
  MODEL_PATH=/ruta/a/network.rpk   Sobreescribe la ruta del modelo .rpk.
  SHOW=1                           Muestra ventana de preview (por defecto no).
"""

import os

# Cuando no se va a mostrar preview, fuerza el backend Qt "offscreen" para
# evitar "Could not load the Qt platform plugin xcb" en modo headless.
if os.getenv("SHOW", "0").lower() not in ("1", "true", "yes"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import json
import math
import time
from datetime import datetime

from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

# -------------------------------------------------
# Configuración
# -------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_MODEL = os.path.join(
    _SCRIPT_DIR,
    "runs", "detect", "runs", "gym_tec_yolo11n", "yolo11n_finetuned",
    "weights", "best_imx_model", "rpk_out", "network.rpk",
)
MODEL = os.getenv("MODEL_PATH", _DEFAULT_MODEL)
if not os.path.exists(MODEL):
    raise SystemExit(
        f"No se encontró el modelo .rpk en:\n  {MODEL}\n\n"
        "Genera el modelo con el flujo de entrenamiento (train.py + imx500-package) "
        "o indica la ruta correcta con la variable de entorno MODEL_PATH, por ejemplo:\n"
        "  MODEL_PATH=/ruta/a/network.rpk python contador_cruce_imx500_standalone.py"
    )

SHOW             = os.getenv("SHOW", "0").lower() in ("1", "true", "yes")
THRESHOLD        = 0.50
LINE_X           = 320
LINE_GAP         = 50
LINE_LEFT        = LINE_X - LINE_GAP
LINE_RIGHT       = LINE_X + LINE_GAP
MAX_DISTANCE     = 120
MAX_MISSES       = 15
PERSON_CLASS_ID  = 0
COUNTER_STATE    = "contador_state.json"


# -------------------------------------------------
# Persistencia del contador (sobrevive a reinicios el mismo día)
# -------------------------------------------------
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
last_detections: list = []
tracks: dict = {}
next_id = 0
contador = _load_counter_state()
_last_date = datetime.now().strftime("%Y-%m-%d")


def _check_midnight_reset():
    """Si cambió el día, reinicia el contador a 0."""
    global contador, _last_date, next_id
    current_date = datetime.now().strftime("%Y-%m-%d")
    if current_date != _last_date:
        contador = 0
        tracks.clear()
        next_id = 0
        _last_date = current_date
        _save_counter_state()
        print("[Reset] Medianoche — contador reiniciado")


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
    _MAX_BOX_AREA = 150_000
    for det in detections:
        x, y, w, h = [int(v) for v in det.box]
        area = w * h
        if area < 1500 or area > _MAX_BOX_AREA:
            continue
        dets.append({"x1": x, "y1": y, "x2": x + w, "y2": y + h,
                     "cx": x + w // 2, "cy": y + h // 2, "conf": det.conf})

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
            tr.update({k: det[k] for k in det})
            tr["misses"] = 0
            usados.add(mejor_id)
        else:
            tracks[next_id] = {**det, "last_outer": None, "via_middle": False, "misses": 0}
            usados.add(next_id)
            next_id += 1

    for tid in list(tracks.keys()):
        if tid not in usados:
            tracks[tid]["misses"] += 1
            if tracks[tid]["misses"] > MAX_MISSES:
                del tracks[tid]

    for tid, tr in tracks.items():
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
            if tr.get("last_outer") == "R" and tr.get("via_middle"):
                if contador > 0:
                    contador -= 1
                print(f"[Salida] contador = {contador}")
            tr["last_outer"] = "L"
            tr["via_middle"] = False
        else:
            if tr.get("last_outer") == "L" and tr.get("via_middle"):
                contador += 1
                print(f"[Entrada] contador = {contador}")
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
            cv2.putText(m.array, f"ID {tid}", (tr["x1"], max(20, tr["y1"] - 8)),
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

print(f"Modelo: {MODEL}")
print(f"SHOW preview: {SHOW}")
print(f"Contador inicial: {contador}")
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
        _check_midnight_reset()

        if contador != prev_contador:
            _save_counter_state()
            prev_contador = contador

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nDetenido por el usuario.")
finally:
    picam2.stop()
