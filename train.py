"""
Entrenamiento / fine-tuning de YOLO26n para el contador del Gym Tec EdoMex.

Uso:
    python train.py                         # entrena y evalúa
    python train.py --export best.pt        # solo exporta a IMX500 (ejecutar en la Pi)

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

import argparse

from ultralytics import YOLO

# -------------------------------------------------
# Configuración — ajusta según tu dataset
# -------------------------------------------------
BASE_MODEL = "yolo11n.pt"          # modelo preentrenado de partida
DATA_YAML  = "./dataset/data.yaml"   # ruta al archivo de configuración del dataset

EPOCHS     = 100                  # máximo de epochs (early stopping puede parar antes)
IMG_SIZE   = 512                   # resolución de entrenamiento
BATCH      = 16                     # RTX 4050 6 GB — batch 8 aún causa OOM con yolo11s

FREEZE     = 10                    # menos capas congeladas → cls head puede adaptarse mejor
LR0        = 0.001                 # LR estándar de fine-tuning; el run anterior con 0.0001 fue demasiado conservador
LRF        = 0.01                  # LR final = LR0 * LRF = 0.00001
WARMUP     = 3                     # epochs de calentamiento antes de aplicar LR completo
PATIENCE   = 15                    # más margen antes de early stopping con más epochs

def export_imx500(model_path: str):
    """Exporta un .pt ya entrenado al formato IMX500. Ejecutar en la Pi."""
    print(f"Exportando {model_path} para IMX500...")
    imx_dir = YOLO(model_path).export(format="imx", data=DATA_YAML)
    print(f"Archivos IMX500 generados en: {imx_dir}")
    print("\nPaso final en la Raspberry Pi:")
    print("  imx500-package packerOut.zip")
    print("  -> genera el .rpk listo para picamera2.")
    print("  -> Actualiza MODEL en contador_cruce_imx500_trained.py con la ruta del .rpk.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", metavar="WEIGHTS", help="Solo exporta el .pt indicado a formato IMX500 (sin entrenar)")
    args = parser.parse_args()

    if args.export:
        export_imx500(args.export)
        raise SystemExit(0)

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
        mosaic=0.0,             # deshabilitado — compone 4 imágenes a 1280×1280 en VRAM
        mixup=0.0,              # deshabilitado — crea arrays 1280×1280 que agotan RAM
        copy_paste=0.0,         # deshabilitado — misma razón
        cache=False,            # no pre-cargar imágenes en RAM/VRAM
        degrees=5.0,            # rotación leve para variaciones de ángulo en la entrada

        # Proyecto
        project="runs/gym_tec_yolo11n",
        name="yolo11n_finetuned",
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
        run_dir  = pathlib.Path("runs/gym_tec_yolo11n/yolo11n_finetuned")
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
        name="yolo11n_finetuned_test",
        exist_ok=True,
        workers=0,
    )
    print(f"mAP50:    {metrics.box.map50:.3f}")
    print(f"mAP50-95: {metrics.box.map:.3f}")

    
    print("\nPara usar el modelo afinado en el contador, cambia en contador_cruce.py:")
    print(f'  MODEL_PATH = "{best_pt}"')
    print(f'\nPara exportar a IMX500 (en la Pi):')
    print(f'  python train.py --export "{best_pt}"')

# Resultados:
# 0.945 yolo11n
# 0.959 yolo11s
# 0.967 yolo11m