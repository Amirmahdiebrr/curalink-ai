"""
app/services/job_store.py

Simple in-memory job store for tracking background analysis jobs.
Not persistent across server restarts - fine for MVP/single-instance use.
"""

import time
import uuid


jobs: dict[str, dict] = {}


def create_job(exam_type: str, user_id: int | None = None) -> str:
    job_id = uuid.uuid4().hex

    jobs[job_id] = {
        "status": "pending",
        "stage": "queued",
        "exam_type": exam_type,
        "user_id": user_id,
        "result": None,
        "error": None,
        "created_at": time.time(),
    }

    return job_id


def update_job(job_id: str, **kwargs):
    if job_id in jobs:
        jobs[job_id].update(kwargs)


def get_job(job_id: str):
    return jobs.get(job_id)