import datetime as dt
import datetime
from datetime import timedelta
from typing import Iterable, List, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from collections import defaultdict
from django.views.generic import ListView, DetailView

from .models import ActivityClass, Booking, Tag, Location, ScheduleRule
from .utils import decode_occurrence_token, expand_rules, make_occurrence_token


def occurrences_for_rules(
    rules: Iterable["ScheduleRule"],
    days_ahead: int = 14,
    tz: Optional[dt.tzinfo] = None,
    from_dt: Optional[dt.datetime] = None,
) -> List[dt.datetime]:
    """
    Expand weekly rules into concrete datetimes for the next `days_ahead` days,
    starting from `from_dt` (default: now). Returns a sorted list (ascending).
    """
    tz = tz or timezone.get_current_timezone()
    start_moment = (from_dt or timezone.now()).astimezone(tz)
    start_date = start_moment.date()
    results: List[dt.datetime] = []
    by_weekday: dict[int, list] = defaultdict(list)

    # Pre-group rules by weekday (0=Mon..6=Sun)
    for r in rules:
        by_weekday[r.weekday].append(r)

    for offset in range(days_ahead + 1):
        day = start_date + dt.timedelta(days=offset)
        wk = day.weekday()
        if wk not in by_weekday:
            continue

        for r in by_weekday[wk]:
            naive = dt.datetime.combine(day, r.time)
            local_dt = timezone.make_aware(naive, tz)  # zoneinfo-safe

            # Skip times earlier than the start moment (same-day guard)
            if local_dt >= start_moment:
                results.append(local_dt)

    results.sort()
    return results



class ActivityClassList(ListView):
    model = ActivityClass
    template_name = "catalog/class_list.html"
    context_object_name = "classes"
    paginate_by = 12

    def get_queryset(self):
        qs = (ActivityClass.objects
              .select_related("location", "coach")
              .prefetch_related("tags", "weekly_rules")
              .order_by("title"))

        q = self.request.GET.get("q", "").strip()
        tag = self.request.GET.get("tag", "").strip()
        city = self.request.GET.get("city", "").strip()
        date_str = self.request.GET.get("date", "").strip()

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        if tag:
            # allow slug or id
            qs = qs.filter(Q(tags__slug=tag) | Q(tags__id__iexact=tag))

        if city:
            qs = qs.filter(location__city__iexact=city)

        if date_str:
            # ISO yyyy-mm-dd; match weekday of that date
            try:
                d = dt.date.fromisoformat(date_str)
                qs = qs.filter(schedulerule__weekday=d.weekday())
            except ValueError:
                pass  # ignore invalid date

        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tag"] = self.request.GET.get("tag", "")
        ctx["city"] = self.request.GET.get("city", "")
        ctx["date"] = self.request.GET.get("date", "")

        # Filter options
        ctx["all_tags"] = Tag.objects.order_by("name")
        ctx["all_cities"] = (Location.objects
                             .values_list("city", flat=True)
                             .distinct().order_by("city"))

        # Next 3 occurrences per class (for cards)
        cards = []
        tz = timezone.get_current_timezone()
        for obj in ctx["classes"]:
            rules = obj.weekly_rules.all()
            next_times = occurrences_for_rules(rules, days_ahead=14, tz=tz)[:3]
            cards.append((obj, next_times))

        ctx["cards"] = cards
        return ctx



class ActivityClassDetail(DetailView):
    model = ActivityClass
    slug_field = "slug"
    context_object_name = "cls"
    template_name = "catalog/class_detail.html"

    def get_queryset(self):
        return (ActivityClass.objects
                .select_related("location", "coach")
                .prefetch_related("tags", "weekly_rules"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start_param = self.request.GET.get("start")
        if start_param:
            try:
                y, m, d = map(int, start_param.split("-"))
                start_dt = timezone.make_aware(datetime.datetime(y, m, d))
            except Exception:
                start_dt = timezone.now()
        else:
            start_dt = timezone.now()

        end_dt = start_dt + timedelta(days=14)
        sessions = expand_rules(self.object, start_dt, end_dt)[:10]
        for session in sessions:
            session["token"] = make_occurrence_token(
                self.object.pk,
                session["start"],
                session["end"],
            )
        ctx["upcoming_sessions"] = sessions
        return ctx


GRACE_PERIOD = dt.timedelta(minutes=5)


@login_required
def book_session(request, slug):
    activity_class = get_object_or_404(ActivityClass, slug=slug)

    if request.method != "POST":
        return redirect(activity_class.get_absolute_url())

    token = request.POST.get("token", "")
    try:
        decoded_class, start_dt, end_dt = decode_occurrence_token(token)
        if decoded_class.pk != activity_class.pk:
            raise ValueError("Token does not match class")
    except Exception:
        messages.error(request, "Invalid or expired session.")
        return redirect(activity_class.get_absolute_url())

    now = timezone.now() - GRACE_PERIOD
    if start_dt < now:
        messages.error(request, "This session has already started.")
        return redirect(activity_class.get_absolute_url())

    already_booked = Booking.objects.filter(
        user=request.user,
        activity_class=activity_class,
        start=start_dt,
    ).exists()

    if already_booked:
        messages.info(request, "You already booked this session.")
        return redirect(activity_class.get_absolute_url())

    Booking.objects.create(
        user=request.user,
        activity_class=activity_class,
        start=start_dt,
        end=end_dt,
    )
    messages.success(request, "Booking confirmed!")
    return redirect(activity_class.get_absolute_url())
