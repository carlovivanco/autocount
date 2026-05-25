#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  export_to_hailo.sh — Compila el YOLO11s afinado a formato Hailo (.hef)
#  para correrlo en el AI HAT+ (acelerador Hailo) con una cámara normal.
#
#  Pipeline:  best.pt  ──(ultralytics)──►  best.onnx  ──(Hailo Model Zoo)──►  .hef
#
#  IMPORTANTE: la compilación DFC NO corre en la Raspberry Pi. Ejecuta este
#  script en una PC x86 (Ubuntu) con el Hailo AI Software Suite / Model Zoo
#  instalado (idealmente dentro del Docker oficial de Hailo). Luego copia el
#  .hef resultante a la Pi, a la carpeta autocount/models/.
#
#  Uso:
#    HW_ARCH=hailo8l bash scripts/export_to_hailo.sh      # AI HAT+ 13 TOPS / AI Kit
#    HW_ARCH=hailo8  bash scripts/export_to_hailo.sh      # AI HAT+ 26 TOPS
#
#  Variables:
#    HW_ARCH    Arquitectura objetivo: hailo8l (default) o hailo8.
#    CKPT       Ruta al best.pt entrenado.
#    CALIB_DIR  Carpeta con imágenes de calibración (recortes del dataset).
#    IMGSZ      Tamaño de entrada (debe coincidir con el entrenamiento: 512).
# ─────────────────────────────────────────────────────────────────────────────
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

HW_ARCH="${HW_ARCH:-hailo8l}"
CKPT="${CKPT:-$REPO_DIR/runs/detect/runs/gym_tec_yolo11s/yolo11s_finetuned/weights/best.pt}"
CALIB_DIR="${CALIB_DIR:-$REPO_DIR/dataset/images/val}"
IMGSZ="${IMGSZ:-512}"
OUT_DIR="$REPO_DIR/models"
HEF_NAME="yolo11s_gym.hef"

echo "▶ Modelo:      $CKPT"
echo "▶ Arch:        $HW_ARCH"
echo "▶ Calibración: $CALIB_DIR"
echo "▶ imgsz:       $IMGSZ"
echo ""

if [ "$HW_ARCH" != "hailo8" ] && [ "$HW_ARCH" != "hailo8l" ]; then
  echo "✗ HW_ARCH inválido: '$HW_ARCH' (usa hailo8 o hailo8l)"; exit 1
fi
if [ ! -f "$CKPT" ]; then
  echo "✗ No se encontró el modelo: $CKPT"; exit 1
fi

mkdir -p "$OUT_DIR"
ONNX_PATH="${CKPT%.pt}.onnx"

# ── 1. Exportar a ONNX con ultralytics ──────────────────────────────────────
echo "[1/3] Exportando a ONNX..."
yolo export model="$CKPT" format=onnx imgsz="$IMGSZ" opset=11

# ── 2. Compilar a .hef con el Hailo Model Zoo ───────────────────────────────
#    yolo11s es una red soportada por el Model Zoo. --classes 1 porque el
#    modelo afinado detecta una sola clase (person). Requiere imágenes de
#    calibración representativas (el dataset de entrenamiento sirve).
echo "[2/3] Compilando a .hef ($HW_ARCH)..."
if ! command -v hailomz >/dev/null 2>&1; then
  echo "✗ 'hailomz' no está disponible. Corre este paso dentro del Hailo AI"
  echo "  Software Suite / Model Zoo (PC x86). Ver https://github.com/hailo-ai/hailo_model_zoo"
  exit 1
fi
hailomz compile yolov11s \
  --ckpt "$ONNX_PATH" \
  --hw-arch "$HW_ARCH" \
  --calib-path "$CALIB_DIR" \
  --classes 1

# ── 3. Colocar el .hef donde lo espera contador_cruce.py ────────────────────
echo "[3/3] Copiando .hef a $OUT_DIR/$HEF_NAME ..."
COMPILED_HEF="$(ls -t ./*.hef 2>/dev/null | head -1 || true)"
if [ -z "$COMPILED_HEF" ]; then
  echo "✗ No se encontró el .hef generado. Revisa la salida de hailomz."; exit 1
fi
cp "$COMPILED_HEF" "$OUT_DIR/$HEF_NAME"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Listo: $OUT_DIR/$HEF_NAME"
echo ""
echo "  Copia este archivo a la Pi (misma ruta autocount/models/) y corre:"
echo "    SHOW=1 HEF_MODEL=models/$HEF_NAME python3 contador_cruce.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
