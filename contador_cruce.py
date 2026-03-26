from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import time

# Modelo
model = YOLO("yolov8n.pt")

# Cámara
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()

time.sleep(2)

# Posición de la línea
LINE_X = 320

# Contador
contador = 0

# Guardar posición anterior de cada ID
posiciones_previas = {}

print("Presiona q para salir")

while True:

    frame = picam2.capture_array()

    results = model.track(
        frame,
        classes=[0],
        persist=True,
        conf=0.4,
        verbose=False
    )

    if results[0].boxes.id is not None:

        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy()

        for box, track_id in zip(boxes, ids):

            x1, y1, x2, y2 = map(int, box)

            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            cv2.circle(frame, (cx, cy), 5, (0,255,0), -1)
            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)

            if track_id in posiciones_previas:

                prev_x = posiciones_previas[track_id]

                # izquierda -> derecha
                if prev_x < LINE_X and cx >= LINE_X:
                    contador -= 1

                # derecha -> izquierda
                elif prev_x > LINE_X and cx <= LINE_X:
                    contador += 1

            posiciones_previas[track_id] = cx

    # Dibujar línea
    cv2.line(frame, (LINE_X,0), (LINE_X,480), (0,0,255), 2)

    # Mostrar contador
    cv2.putText(
        frame,
        f"Contador: {contador}",
        (20,40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255,0,0),
        2
    )

    cv2.imshow("Conteo por cruce", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
picam2.stop()
