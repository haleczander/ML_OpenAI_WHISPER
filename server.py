from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, request, send_file
from flask_sock import Sock
from whisper_backend import BackendConfig, load_model, transcribe_text


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
ITEMS_PATH = DATA_DIR / "items.json"
CERT_DIR = BASE_DIR / "certs"
CERT_PATH = CERT_DIR / "local.pem"
KEY_PATH = CERT_DIR / "local-key.pem"

MODEL_NAME = os.getenv("WHISPER_MODEL", "large-v3")
LANGUAGE = "fr"
TASK = "transcribe"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_items() -> List[Dict[str, Any]]:
    if not ITEMS_PATH.exists():
        return []
    try:
        return json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_items(items: List[Dict[str, Any]]) -> None:
    ITEMS_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)


def load_stt_model():
    return load_model(BackendConfig(model_name=MODEL_NAME))


def ffmpeg_exists() -> bool:
    return shutil.which("ffmpeg") is not None


def convert_to_mp3(src_path: Path, dst_path: Path) -> bool:
    if not ffmpeg_exists():
        return False
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src_path), str(dst_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def transcribe_audio(model, audio_path: Path) -> str:
    return transcribe_text(
        model,
        str(audio_path),
        language=LANGUAGE,
        task=TASK,
        temperature=0.0,
    )


def read_transcript(item: Dict[str, Any]) -> str:
    path_value = item.get("transcript_path")
    if not path_value:
        return ""
    path = BASE_DIR / path_value
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


app = Flask(__name__, static_folder="static", static_url_path="/static")
sock = Sock(app)
MODEL, BACKEND_INFO = load_stt_model()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "backend": BACKEND_INFO["backend"],
            "device": BACKEND_INFO["device"],
            "compute_type": BACKEND_INFO["compute_type"],
            "model": BACKEND_INFO["model"],
        }
    )


@app.route("/api/items", methods=["GET"])
def list_items():
    items = load_items()
    items = sorted(items, key=lambda x: x["created_at"], reverse=True)
    response = []
    for item in items:
        response_item = dict(item)
        response_item["transcript"] = read_transcript(item)
        response.append(response_item)
    return jsonify(response)


@app.route("/api/upload", methods=["POST"])
def upload():
    ensure_dirs()
    if "audio" not in request.files:
        return jsonify({"error": "missing audio file"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "empty filename"}), 400

    item_id = uuid.uuid4().hex
    raw_path = AUDIO_DIR / f"{item_id}.webm"
    audio_file.save(raw_path)

    audio_path = raw_path
    mp3_path = AUDIO_DIR / f"{item_id}.mp3"
    if convert_to_mp3(raw_path, mp3_path):
        audio_path = mp3_path

    transcript = transcribe_audio(MODEL, audio_path)
    transcript_path = TRANSCRIPT_DIR / f"{item_id}.txt"
    transcript_path.write_text(transcript + "\n", encoding="utf-8")

    item = {
        "id": item_id,
        "created_at": utc_now(),
        "audio_path": str(audio_path.relative_to(BASE_DIR)),
        "audio_url": f"/audio/{item_id}",
        "transcript_path": str(transcript_path.relative_to(BASE_DIR)),
    }
    items = load_items()
    items.append(item)
    save_items(items)
    response_item = dict(item)
    response_item["transcript"] = transcript
    return jsonify(response_item), 201


@app.route("/audio/<item_id>", methods=["GET"])
def get_audio(item_id: str):
    items = load_items()
    for item in items:
        if item["id"] == item_id:
            audio_path = BASE_DIR / item["audio_path"]
            if audio_path.exists():
                return send_file(audio_path, as_attachment=False)
            return jsonify({"error": "audio not found"}), 404
    return jsonify({"error": "item not found"}), 404


def transcribe_buffer(model, buffer_bytes: bytes, temp_path: Path) -> str:
    temp_path.write_bytes(buffer_bytes)
    return transcribe_audio(model, temp_path)


@sock.route("/ws")
def stream(ws):
    if not ffmpeg_exists():
        ws.send(json.dumps({"type": "error", "message": "ffmpeg_missing"}))
        return

    session_id = uuid.uuid4().hex
    temp_path = DATA_DIR / f"stream_{session_id}.webm"
    buffer_bytes = bytearray()
    ws.send(json.dumps({"type": "ready"}))

    while True:
        message = ws.receive()
        if message is None:
            break

        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                continue
            if payload.get("type") == "stop":
                break
            continue

        if isinstance(message, bytes):
            buffer_bytes.extend(message)
            continue

    if buffer_bytes:
        ensure_dirs()
        item_id = uuid.uuid4().hex
        raw_path = AUDIO_DIR / f"{item_id}.webm"
        raw_path.write_bytes(buffer_bytes)

        audio_path = raw_path
        mp3_path = AUDIO_DIR / f"{item_id}.mp3"
        if convert_to_mp3(raw_path, mp3_path):
            audio_path = mp3_path

        transcript = transcribe_audio(MODEL, audio_path)
        transcript_path = TRANSCRIPT_DIR / f"{item_id}.txt"
        transcript_path.write_text(transcript + "\n", encoding="utf-8")

        item = {
            "id": item_id,
            "created_at": utc_now(),
            "audio_path": str(audio_path.relative_to(BASE_DIR)),
            "audio_url": f"/audio/{item_id}",
            "transcript_path": str(transcript_path.relative_to(BASE_DIR)),
        }
        items = load_items()
        items.append(item)
        save_items(items)

        ws.send(json.dumps({"type": "final", "item": item, "transcript": transcript}))


@app.route("/api/items/<item_id>", methods=["DELETE"])
def delete_item(item_id: str):
    items = load_items()
    remaining = []
    target = None
    for item in items:
        if item["id"] == item_id:
            target = item
        else:
            remaining.append(item)

    if not target:
        return jsonify({"error": "item not found"}), 404

    audio_path = BASE_DIR / target.get("audio_path", "")
    transcript_path = BASE_DIR / target.get("transcript_path", "")
    if audio_path.exists():
        audio_path.unlink()
    if transcript_path.exists():
        transcript_path.unlink()

    save_items(remaining)
    return jsonify({"status": "deleted", "id": item_id})


@app.route("/", methods=["GET"])
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    ensure_dirs()
    if not CERT_PATH.exists() or not KEY_PATH.exists():
        raise SystemExit(
            "Missing HTTPS certs. Create certs/local.pem and certs/local-key.pem."
        )
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
        ssl_context=(str(CERT_PATH), str(KEY_PATH)),
    )
