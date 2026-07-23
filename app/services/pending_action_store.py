"""
app/services/pending_action_store.py

In-memory store که اطلاعات لازم برای انجام واقعی یک اکشن pay-per-use
(تحلیل آزمایش / برنامه غذایی / آماده‌سازی ویزیت) را بعد از برگشت کاربر
از درگاه زرین‌پال نگه می‌دارد. کلید = Payment.id
"""

import time
import threading

_actions: dict[int, dict] = {}
_lock = threading.Lock()

ACTION_MAX_AGE_SECONDS = 60 * 60 * 2  # ۲ ساعت


def save(payment_id: int, data: dict):
    with _lock:
        _actions[payment_id] = {
            "data": data,
            "result_type": None,
            "result_id": None,
            "error": None,
            "created_at": time.time(),
        }


def get(payment_id: int) -> dict | None:
    with _lock:
        return _actions.get(payment_id)


def update(payment_id: int, **kwargs):
    with _lock:
        action = _actions.get(payment_id)
        if action is None:
            return
        action.update(kwargs)


def delete(payment_id: int):
    with _lock:
        _actions.pop(payment_id, None)


def purge_old():
    now = time.time()
    with _lock:
        expired = [pid for pid, a in _actions.items() if now - a.get("created_at", now) > ACTION_MAX_AGE_SECONDS]
        for pid in expired:
            del _actions[pid]

    if expired:
        print(f"[PendingActionStore] Purged {len(expired)} expired action(s)", flush=True)