import cv2
import math
import time

from picamera2 import MappedArray, Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics

# -------------------------------------------------
# Configuración
# -------------------------------------------------
MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
THRESHOLD = 0.55
LINE_X = 320              # línea vertical
MAX_DISTANCE = 80         # distancia máxima para asociar detecciones
MAX_MISSES = 10           # frames que aguanta un track sin verse

# COCO: person = 0
PERSON_CLASS_ID = 0

last_detections = []
tracks = {}
next_id = 0
contador = 0


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
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)

        # filtro por tamaño mínimo
        if w * h < 1500:
            continue

        cx = x + w // 2
        cy = y + h // 2

        dets.append({
            "x1": x,
            "y1": y,
            "x2": x + w,
            "y2": y + h,
            "cx": cx,
            "cy": cy,
            "conf": det.conf,
        })

    usados = set()
    ids_tracks = list(tracks.keys())

    # Asociar detecciones a tracks por cercanía
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
                "cx": det["cx"],
                "cy": det["cy"],
                "prev_cx": det["cx"],
                "x1": det["x1"],
                "y1": det["y1"],
                "x2": det["x2"],
                "y2": det["y2"],
                "conf": det["conf"],
                "misses": 0,
                "counted": False,
            }
            usados.add(next_id)
            next_id += 1

    # Incrementar misses
    for tid in list(tracks.keys()):
        if tid not in usados:
            tracks[tid]["misses"] += 1
            if tracks[tid]["misses"] > MAX_MISSES:
                del tracks[tid]

    # Revisar cruces
    for tid, tr in tracks.items():
        prev_cx = tr["prev_cx"]
        cx = tr["cx"]

        # izquierda -> derecha = -1
        if not tr["counted"] and prev_cx < LINE_X <= cx:
            contador -= 1
            tr["counted"] = True

        # derecha -> izquierda = +1
        elif not tr["counted"] and prev_cx > LINE_X >= cx:
            contador += 1
            tr["counted"] = True

        # volver a habilitar conteo si se aleja de la línea
        if abs(cx - LINE_X) > 100:
            tr["counted"] = False


def draw_overlay(request, stream="main"):
    with MappedArray(request, stream) as m:
        # línea
        h, w = m.array.shape[:2]
        cv2.line(m.array, (LINE_X, 0), (LINE_X, h), (0, 0, 255), 2)

        # contador
        cv2.putText(
            m.array,
            f"Contador: {contador}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 0, 0),
            2,
        )

        # tracks
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

print("Presiona Ctrl+C para salir")

try:
    while True:
        metadata = picam2.capture_metadata()
        detections = parse_detections(metadata)
        actualizar_tracks(detections)
        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    picam2.stop()
