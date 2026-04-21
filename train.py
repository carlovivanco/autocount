"""
Entrenamiento / fine-tuning de YOLO26n para el contador del Gym Tec EdoMex.

Requisitos:
    pip install ultralytics

Estructura esperada del dataset:
    dataset/
    ├── images/
    │   ├── train/   (70 % de las fotos)
    │   ├── val/     (15 % de las fotos)
    │   └── test/    (15 % de las fotos)
    ├── labels/
    │   ├── train/   (archivos .txt generados por Roboflow)
    │   ├── val/
    │   └── test/
    └── data.yaml
"""

from ultralytics import YOLO

# -------------------------------------------------
# Configuración — ajusta según tu dataset
# -------------------------------------------------
BASE_MODEL = "yolo26n.pt"          # modelo preentrenado de partida
DATA_YAML  = "dataset/data.yaml"   # ruta al archivo de configuración del dataset

EPOCHS     = 100                  # máximo de epochs (early stopping puede parar antes)
IMG_SIZE   = 640                   # resolución de entrenamiento
BATCH      = 16                    # RTX 4050 con yolo26n lo soporta; gradientes más estables

FREEZE     = 10                    # menos capas congeladas → cls head puede adaptarse mejor
LR0        = 0.001                 # LR estándar de fine-tuning; el run anterior con 0.0001 fue demasiado conservador
LRF        = 0.01                  # LR final = LR0 * LRF = 0.00001
WARMUP     = 3                     # epochs de calentamiento antes de aplicar LR completo
PATIENCE   = 15                    # más margen antes de early stopping con más epochs

if __name__ == "__main__":
    # -------------------------------------------------
    # Fine-tuning
    # -------------------------------------------------
    model = YOLO(BASE_MODEL)

    result = model.train(
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

        # Augmentation — resultados anteriores: P=0.95, R=0.889
        # Objetivo: subir recall cerrando la brecha con precision
        augment=True,
        label_smoothing=0.1,    # reduce sobreconfianza → mejora recall
        mixup=0.1,              # mezcla sintética de dos imágenes
        copy_paste=0.2,         # más personas sintéticas en escena (anterior: 0.1)
        degrees=5.0,            # rotación leve para variaciones de ángulo en la entrada

        # Proyecto
        project="runs/gym_tec",
        name="yolo26n_finetuned",
        exist_ok=True,

        workers=0,          # evita spawning de procesos extra en Windows
    )

    trainer = model.trainer if hasattr(model, "trainer") and model.trainer is not None else result.trainer if hasattr(result, "trainer") else None
    if trainer is not None:
        best_pt  = str(trainer.best)
        save_dir = str(trainer.save_dir.parent)
    else:
        # val()-only result (exist_ok=True, training already done) — locate weights manually
        import pathlib
        run_dir  = pathlib.Path("runs/gym_tec/yolo26n_finetuned")
        best_pt  = str(run_dir / "weights" / "best.pt")
        save_dir = str(run_dir.parent)

    print("\nEntrenamiento finalizado.")
    print(f"Modelo guardado en: {best_pt}")

    # -------------------------------------------------
    # Evaluación en el conjunto de test
    # -------------------------------------------------
    print("\nEvaluando en el conjunto de test...")
    model = YOLO(best_pt)
    metrics = model.val(
        data=DATA_YAML,
        split="test",
        project=save_dir,
        name="yolo26n_finetuned_test",
        exist_ok=True,
        workers=0,
    )
    print(f"mAP50:    {metrics.box.map50:.3f}")
    print(f"mAP50-95: {metrics.box.map:.3f}")

    print("\nPara usar el modelo afinado en el contador, cambia en contador_cruce.py:")
    print(f'  MODEL_PATH = "{best_pt}"')
