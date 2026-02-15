from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_sock import Sock

from src.application.container import AppContainer


BASE_DIR = Path(__file__).resolve().parent
CERT_DIR = BASE_DIR / "certs"
CERT_PATH = CERT_DIR / "local.pem"
KEY_PATH = CERT_DIR / "local-key.pem"


app = Flask(__name__, static_folder="static", static_url_path="/static")
sock = Sock(app)
container = AppContainer(base_dir=BASE_DIR)
container.file_persist.ensure_dirs()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "device": container.transcriber.device,
            "model": container.transcriber.model_name,
        }
    )


@app.route("/api/items", methods=["GET"])
def list_items():
    return jsonify(container.list_items_use_case.execute())


@app.route("/api/items/<item_id>", methods=["GET"])
def get_item(item_id: str):
    item = container.get_item_use_case.execute(item_id)
    if not item:
        return jsonify({"error": "item not found"}), 404
    return jsonify(item)


@app.route("/api/upload", methods=["POST"])
def upload():
    if "audio" not in request.files:
        return jsonify({"error": "missing audio file"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "empty filename"}), 400

    item, transcript = container.transcribe_use_case.from_upload(audio_file)
    response_item = item.to_dict()
    response_item["transcript"] = transcript
    return jsonify(response_item), 201


@app.route("/audio/<item_id>", methods=["GET"])
def get_audio(item_id: str):
    audio_path = container.get_audio_path_use_case.execute(item_id)
    if not audio_path:
        return jsonify({"error": "item not found or audio not found"}), 404
    return send_file(audio_path, as_attachment=False)


@sock.route("/ws")
def stream(ws):
    ws.send(json.dumps({"type": "ready"}))
    buffer_bytes = bytearray()

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

    if not buffer_bytes:
        return

    item, transcript = container.transcribe_use_case.from_bytes(bytes(buffer_bytes), extension=".webm")
    ws.send(
        json.dumps(
            {
                "type": "final",
                "item": item.to_dict(),
                "transcript": transcript,
            }
        )
    )


@app.route("/api/items/<item_id>", methods=["DELETE"])
def delete_item(item_id: str):
    deleted = container.delete_item_use_case.execute(item_id)
    if not deleted:
        return jsonify({"error": "item not found"}), 404
    return jsonify({"status": "deleted", "id": item_id})


@app.route("/", methods=["GET"])
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
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
