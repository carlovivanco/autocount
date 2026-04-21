import cv2
from inference_sdk import InferenceHTTPClient

# Initialize client
client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="gxFkHzwiVaAQZShdPwmQ"
)

# Open laptop camera (index 0)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print("Error: No se pudo abrir la camara")
    exit(1)

print("Camara abierta. Presiona 'q' para salir.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: No se pudo leer frame")
        break

    # Send frame to Roboflow workflow
    result = client.run_workflow(
        workspace_name="thesis-xvqdl",
        workflow_id="detect-count-and-visualize",
        images={"image": frame},
    )

    # Print detection data
    print(f"Result: {result}")

    # Show the original frame
    cv2.imshow("Deteccion en vivo", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
