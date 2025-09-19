from __future__ import annotations

import datetime as dt
from typing import Dict, List

from django.utils import timezone

from .models import ScheduleRule


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

            sessions.append({
                "start": start,
                "end": start,
                "rule": rule,
            })

    sessions.sort(key=lambda item: item["start"])
    return sessions
