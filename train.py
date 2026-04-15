"""
Entrenamiento / fine-tuning de YOLO26n para el contador del Gym Tec EdoMex.

Requisitos:
    pip install ultralytics

Estructura esperada del dataset:
    dataset/
    ├── images/
    │   ├── train/   (80 % de las fotos)
    │   └── val/     (20 % de las fotos)
    ├── labels/
    │   ├── train/   (archivos .txt generados por Roboflow)
    │   └── val/
    └── data.yaml

Contenido mínimo de data.yaml:
    path: ./dataset
    train: images/train
    val:   images/val
    nc: 1
    names: ['person']

Para etiquetar fotos gratis: https://roboflow.com
  → Exportar en formato "YOLOv8"
"""

from ultralytics import YOLO

# -------------------------------------------------
# Configuración — ajusta según tu dataset
# -------------------------------------------------
BASE_MODEL = "yolo26n.pt"          # modelo preentrenado de partida
DATA_YAML  = "dataset/data.yaml"   # ruta al archivo de configuración del dataset

EPOCHS     = 50                    # máximo de epochs (early stopping puede parar antes)
IMG_SIZE   = 640                   # resolución de entrenamiento
BATCH      = 8                     # bajo para no saturar RAM (sube a 16 si tienes >8 GB)

FREEZE     = 20                    # capas congeladas del backbone (no se modifican)
LR0        = 0.0001                # learning rate inicial muy bajo → no sobreescribe COCO
LRF        = 0.01                  # learning rate final (fracción de LR0)
WARMUP     = 3                     # epochs de calentamiento antes de aplicar LR completo
PATIENCE   = 10                    # early stopping: para si no mejora en N epochs seguidos

# -------------------------------------------------
# Fine-tuning
# -------------------------------------------------
model = YOLO(BASE_MODEL)

model.train(
    data=DATA_YAML,
    epochs=EPOCHS,
    imgsz=IMG_SIZE,
    batch=BATCH,
    classes=[0],            # solo personas (clase 0 de COCO)

    # Preservar accuracy original
    freeze=FREEZE,          # congela backbone, entrena solo el detection head
    lr0=LR0,                # learning rate conservador para no destruir lo aprendido
    lrf=LRF,
    warmup_epochs=WARMUP,
    patience=PATIENCE,      # early stopping automático

    # Augmentation para generalizar mejor con pocas fotos
    augment=True,
    mixup=0.1,              # mezcla sintética de dos imágenes
    copy_paste=0.1,         # pega personas de una foto en otra

    # Proyecto
    project="runs/gym_tec",
    name="yolo26n_finetuned",
    exist_ok=True,
)

print("\nEntrenamiento finalizado.")
print("Modelo guardado en: runs/gym_tec/yolo26n_finetuned/weights/best.pt")
print("\nPara usar el modelo afinado en el contador, cambia en contador_cruce.py:")
print('  MODEL_PATH = "runs/gym_tec/yolo26n_finetuned/weights/best.pt"')
