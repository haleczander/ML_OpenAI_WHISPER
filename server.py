from __future__ import annotations
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
import uuid

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
transcribe_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="transcribe")
jobs_lock = Lock()
jobs: dict[str, dict[str, str]] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cleanup_jobs() -> None:
    with jobs_lock:
        stale_ids: list[str] = []
        for job_id, job in jobs.items():
            if job["status"] in {"done", "failed"}:
                finished_at = job.get("finished_at")
                if not finished_at:
                    continue
                try:
                    finished_ts = datetime.fromisoformat(finished_at).timestamp()
                except ValueError:
                    continue
                if (time.time() - finished_ts) > 600:
                    stale_ids.append(job_id)
        for stale_id in stale_ids:
            jobs.pop(stale_id, None)


def list_active_jobs() -> list[dict[str, str]]:
    cleanup_jobs()
    with jobs_lock:
        active = [
            dict(job)
            for job in jobs.values()
            if job["status"] in {"queued", "running"}
        ]
    active.sort(key=lambda j: j["submitted_at"], reverse=False)
    return active


def run_transcription_job(job_id: str, payload: bytes, suffix: str) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = utc_now()
        submitted_at = job.get("submitted_at", utc_now())
    try:
        item, _ = container.transcribe_use_case.from_bytes(payload, suffix, submitted_at=submitted_at)
        with jobs_lock:
            job = jobs.get(job_id)
            if not job:
                return
            job["status"] = "done"
            job["finished_at"] = utc_now()
            job["item_id"] = item.id
    except Exception as exc:
        with jobs_lock:
            job = jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["finished_at"] = utc_now()
            job["error"] = str(exc)


def run_regenerate_job(job_id: str, item_id: str) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = utc_now()
    try:
        success, result = container.regenerate_transcript_use_case.execute(item_id)
        with jobs_lock:
            job = jobs.get(job_id)
            if not job:
                return
            if success:
                job["status"] = "done"
                job["finished_at"] = utc_now()
                job["item_id"] = item_id
            else:
                job["status"] = "failed"
                job["finished_at"] = utc_now()
                job["error"] = result
    except Exception as exc:
        with jobs_lock:
            job = jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["finished_at"] = utc_now()
            job["error"] = str(exc)


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


@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    return jsonify(list_active_jobs())


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

    payload = audio_file.read()
    suffix = Path(audio_file.filename).suffix.lower() or ".webm"
    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "kind": "upload",
            "status": "queued",
            "submitted_at": utc_now(),
            "started_at": "",
            "finished_at": "",
            "item_id": "",
            "error": "",
        }
    transcribe_executor.submit(
        run_transcription_job,
        job_id,
        payload,
        suffix,
    )
    return jsonify({"status": "processing", "job": jobs[job_id]}), 202


@app.route("/audio/<item_id>", methods=["GET"])
def get_audio(item_id: str):
    audio_path = container.get_audio_path_use_case.execute(item_id)
    if not audio_path:
        return jsonify({"error": "item not found or audio not found"}), 404
    return send_file(audio_path, as_attachment=False)


@app.route("/api/items/<item_id>/transcript.txt", methods=["GET"])
def download_transcript(item_id: str):
    transcript_path = container.get_transcript_path_use_case.execute(item_id)
    if not transcript_path:
        return jsonify({"error": "item not found or transcript not found"}), 404
    return send_file(
        transcript_path,
        as_attachment=True,
        download_name=f"{item_id}.txt",
        mimetype="text/plain; charset=utf-8",
    )


@app.route("/api/items/<item_id>/regenerate", methods=["POST"])
def regenerate_item_transcript(item_id: str):
    item = container.get_item_use_case.execute(item_id)
    if not item:
        return jsonify({"error": "item not found"}), 404

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "kind": "regenerate",
            "status": "queued",
            "submitted_at": utc_now(),
            "started_at": "",
            "finished_at": "",
            "item_id": item_id,
            "error": "",
        }
    transcribe_executor.submit(run_regenerate_job, job_id, item_id)
    return jsonify({"status": "processing", "job": jobs[job_id]}), 202


@sock.route("/ws/items")
def ws_items(ws):
    previous_items: dict[str, dict] = {}
    previous_jobs: dict[str, dict] = {}

    initial_items = container.list_items_use_case.execute()
    initial_jobs = list_active_jobs()
    previous_items = {item["id"]: item for item in initial_items}
    previous_jobs = {job["id"]: job for job in initial_jobs}
    try:
        ws.send(
            json.dumps(
                {"type": "init", "items": initial_items, "jobs": initial_jobs},
                ensure_ascii=False,
            )
        )
    except Exception:
        return

    while True:
        items = container.list_items_use_case.execute()
        jobs_payload = list_active_jobs()
        current_items = {item["id"]: item for item in items}
        current_jobs = {job["id"]: job for job in jobs_payload}

        ops: list[dict] = []

        for item_id, item in current_items.items():
            if item_id not in previous_items or previous_items[item_id] != item:
                ops.append({"entity": "item", "action": "upsert", "item": item})
        for item_id in previous_items.keys():
            if item_id not in current_items:
                ops.append({"entity": "item", "action": "delete", "id": item_id})

        for job_id, job in current_jobs.items():
            if job_id not in previous_jobs or previous_jobs[job_id] != job:
                ops.append({"entity": "job", "action": "upsert", "job": job})
        for job_id in previous_jobs.keys():
            if job_id not in current_jobs:
                ops.append({"entity": "job", "action": "delete", "id": job_id})

        if ops:
            try:
                ws.send(json.dumps({"type": "ops", "ops": ops}, ensure_ascii=False))
            except Exception:
                break
            previous_items = current_items
            previous_jobs = current_jobs
        time.sleep(1.0)


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
