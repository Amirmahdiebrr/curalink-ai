"""
app/services/job_store.py

Simple in-memory job store for tracking background analysis jobs
(status, stage, result, errors) keyed by job_id.
"""

import uuid
import time
import threading

_jobs: dict[str, dict] = {}
_lock = threading.Lock()

JOB_MAX_AGE_SECONDS = 60 * 60 * 2  # ۲ ساعت


def create_job(exam_type: str | None, user_id: int | None = None) -> str:
    job_id = uuid.uuid4().hex

    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "exam_type": exam_type,
            "user_id": user_id,
            "status": "pending",
            "stage": "pending",
            "result": None,
            "error": None,
            "created_at": time.time(),
        }

    return job_id


def update_job(job_id: str, **kwargs):
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(kwargs)


def get_job(job_id: str) -> dict | None:
    with _lock:
        return _jobs.get(job_id)


def purge_old_jobs():
    now = time.time()
    with _lock:
        expired = [
            jid for jid, job in _jobs.items()
            if now - job.get("created_at", now) > JOB_MAX_AGE_SECONDS
        ]
        for jid in expired:
            del _jobs[jid]

    if expired:
        print(f"[JobStore] Purged {len(expired)} expired job(s)", flush=True)