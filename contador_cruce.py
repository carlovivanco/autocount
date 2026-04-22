import asyncio
import base64
import csv
import cv2
import io
import json
import os
import threading
import time
from datetime import datetime, timedelta

import joblib
import pandas as pd
import websockets
from picamera2 import Picamera2
from sklearn.ensemble import RandomForestClassifier
from ultralytics import YOLO

# -------------------------------------------------
# Configuración
# -------------------------------------------------
MODEL_PATH       = "yolo26n.pt"
CONFIDENCE       = 0.4
LINE_X           = 320
LINE_RESET_DIST  = 100
FRAME_W, FRAME_H = 640, 480

WS_PORT          = 8765
PARQUET_FILE     = "conteo_horario.parquet"
ML_MODEL_FILE    = "peak_model.joblib"
SAMPLE_INTERVAL  = 60        # segundos entre muestras
RETRAIN_DAYS     = 14        # reentrenar cada N días

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# -------------------------------------------------
# Estado global
# -------------------------------------------------
contador = 0
prev_cx: dict[int, int] = {}
crossed: dict[int, bool] = {}

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
        await websocket.send(json.dumps({"count": contador, "peak_prediction": _current_peak_prediction()}))
        async for raw in websocket:
            try:
                data = json.loads(raw)
                cmd = data.get("command", "")
                if cmd == "increment":
                    contador += 1
                    await _broadcast(contador)
                elif cmd == "decrement":
                    contador -= 1
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
    global _last_sample_time, _last_hour, _hourly_samples

    now_ts = time.time()
    now_dt = datetime.fromtimestamp(now_ts)
    current_hour = now_dt.replace(minute=0, second=0, microsecond=0)

    if now_ts - _last_sample_time >= SAMPLE_INTERVAL:
        _hourly_samples.append(contador)
        _last_sample_time = now_ts

    if current_hour != _last_hour:
        if _hourly_samples:
            avg = sum(_hourly_samples) / len(_hourly_samples)
            row = {
                "timestamp":          _last_hour.strftime("%Y-%m-%d %H:%M"),
                "hora":               _last_hour.hour,
                "dia_semana":         _last_hour.weekday(),
                "dia_nombre":         DIAS[_last_hour.weekday()],
                "promedio_personas":  round(avg, 2),
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
# Inicio – cámara, modelo, servicios
# -------------------------------------------------
model = YOLO(MODEL_PATH)

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (FRAME_W, FRAME_H), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(2)

threading.Thread(target=_start_ws_server, daemon=True).start()
print("Presiona q para salir")

# -------------------------------------------------
# Bucle principal
# -------------------------------------------------
prev_contador = contador

try:
    while True:
        frame = picam2.capture_array()

        results = model.track(
            frame,
            classes=[0],
            persist=True,
            conf=CONFIDENCE,
            verbose=False,
        )

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids   = results[0].boxes.id.cpu().numpy().astype(int)

            for box, tid in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                cv2.putText(frame, f"ID {tid}", (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                if tid in prev_cx:
                    px = prev_cx[tid]
                    already = crossed.get(tid, False)
                    if not already and px < LINE_X <= cx:
                        contador -= 1
                        crossed[tid] = True
                    elif not already and px > LINE_X >= cx:
                        contador += 1
                        crossed[tid] = True
                    if abs(cx - LINE_X) > LINE_RESET_DIST:
                        crossed[tid] = False
                prev_cx[tid] = cx

        active_ids = (
            set(results[0].boxes.id.cpu().numpy().astype(int))
            if results[0].boxes.id is not None else set()
        )
        for tid in list(prev_cx):
            if tid not in active_ids:
                del prev_cx[tid]
                crossed.pop(tid, None)

        cv2.line(frame, (LINE_X, 0), (LINE_X, FRAME_H), (0, 0, 255), 2)
        cv2.putText(frame, f"Contador: {contador}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
        cv2.imshow("Conteo - Gym Tec EdoMex", frame)

        if contador != prev_contador:
            broadcast_count()
            prev_contador = contador

        _record_sample()

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    pass

finally:
    cv2.destroyAllWindows()
    picam2.stop()
