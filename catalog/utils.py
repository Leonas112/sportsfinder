from __future__ import annotations

import datetime as dt
import json
from typing import Dict, List, Tuple

from django.utils import timezone
from django.core.signing import BadSignature, Signer

from .models import ActivityClass, ScheduleRule


DEFAULT_SESSION_DURATION = dt.timedelta(hours=1)


SESSION_TOKEN_SALT = "catalog.session-token"


def _ensure_aware(dt_value: dt.datetime) -> dt.datetime:
    if dt_value.tzinfo is None:
        return timezone.make_aware(dt_value, dt.timezone.utc)
    return dt_value


def make_occurrence_token(
    activity_class_id: int,
    start_dt: dt.datetime,
    end_dt: dt.datetime,
    signer: Signer | None = None,
) -> str:
    """Sign and return a token that encodes a single class occurrence."""

    start_dt = _ensure_aware(start_dt).astimezone(dt.timezone.utc)
    end_dt = _ensure_aware(end_dt).astimezone(dt.timezone.utc)

    if start_dt >= end_dt:
        raise ValueError("Session start must be earlier than end.")

    signer = signer or Signer(salt=SESSION_TOKEN_SALT)
    payload = json.dumps(
        {
            "class_id": activity_class_id,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return signer.sign(payload)


def decode_occurrence_token(
    token: str,
    signer: Signer | None = None,
) -> Tuple[ActivityClass, dt.datetime, dt.datetime]:
    """Decode, validate, and return the occurrence payload for booking."""

    signer = signer or Signer(salt=SESSION_TOKEN_SALT)

    try:
        raw_payload = signer.unsign(token)
    except BadSignature as exc:
        raise ValueError("Invalid or tampered session token.") from exc

    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Malformed session token payload.") from exc

    required_keys = {"class_id", "start", "end"}
    if not required_keys.issubset(data):
        raise ValueError("Incomplete session token payload.")

    try:
        activity_class = ActivityClass.objects.get(pk=data["class_id"])
    except ActivityClass.DoesNotExist as exc:
        raise ValueError("Session token references an unknown class.") from exc

    try:
        start_dt = dt.datetime.fromisoformat(data["start"])
        end_dt = dt.datetime.fromisoformat(data["end"])
    except ValueError as exc:
        raise ValueError("Session token contains invalid timestamps.") from exc

    start_dt = _ensure_aware(start_dt).astimezone(timezone.get_current_timezone())
    end_dt = _ensure_aware(end_dt).astimezone(timezone.get_current_timezone())

    if start_dt >= end_dt:
        raise ValueError("Session start must be earlier than end.")

    now = timezone.now().astimezone(timezone.get_current_timezone())
    if start_dt < now:
        raise ValueError("Session token points to a past occurrence.")
    if start_dt > now + dt.timedelta(days=60):
        raise ValueError("Session token is outside the 60-day booking window.")

    return activity_class, start_dt, end_dt


def expand_rules(activity_class, start_dt: dt.datetime, end_dt: dt.datetime) -> List[Dict[str, dt.datetime]]:
    """Expand weekly `ScheduleRule`s into concrete sessions between the given bounds.

    Returns a list of dicts shaped like ``{"start": datetime, "end": datetime}``,
    sorted ascending by ``start``. The body currently implements a basic weekly
    recurrence using each rule's ``next_occurrences`` helper.
    """

    tz = timezone.get_current_timezone()
    start_dt = start_dt.astimezone(tz)
    end_dt = end_dt.astimezone(tz)

    sessions: List[Dict[str, dt.datetime]] = []
    span_days = max((end_dt - start_dt).days + 1, 1)
    approx_count = span_days // 7 + 8  # buffer to account for interval rules

    rules = ScheduleRule.objects.filter(activity_class=activity_class)
    for rule in rules.select_related("activity_class"):
        if not getattr(rule, "active", True) or not rule.time:
            continue

        occurrences = rule.next_occurrences(count=approx_count, from_date=start_dt.date())
        for occ_date in occurrences:
            naive_start = dt.datetime.combine(occ_date, rule.time)
            start = timezone.make_aware(naive_start, tz)
            if start < start_dt:
                continue
            if start >= end_dt:
                break

            end = start + DEFAULT_SESSION_DURATION
            class_id = getattr(activity_class, "pk", None) or rule.activity_class_id
            sessions.append({
                "start": start,
                "end": end,
                "rule": rule,
                "token": make_occurrence_token(class_id, start, end),
            })

    sessions.sort(key=lambda item: item["start"])
    return sessions
