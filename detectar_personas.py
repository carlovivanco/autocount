"""
Detección de personas en tiempo real con YOLO26n.
Sin contador, sin WebSocket — solo detección pura.

Requisitos:
    pip install ultralytics picamera2

Controles:
    q  →  salir
"""

from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import time

MODEL_PATH = "yolo26n.pt"   # se descarga automáticamente la primera vez
CONFIDENCE = 0.4
FRAME_W, FRAME_H = 640, 480

model = YOLO(MODEL_PATH)

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (FRAME_W, FRAME_H), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(2)

print("Detectando personas... Presiona q para salir")

while True:
    frame = picam2.capture_array()

    results = model(frame, classes=[0], conf=CONFIDENCE, verbose=False)

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame,
            f"Persona {conf:.0%}",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
        )

    total = len(results[0].boxes)
    cv2.putText(
        frame,
        f"Personas detectadas: {total}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
    )

    cv2.imshow("Deteccion de personas - YOLO26n", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
picam2.stop()
