import datetime as dt
from typing import Iterable, Dict, List

from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView, DetailView

from .models import ActivityClass, Tag, Location, ScheduleRule


def occurrences_for_rules(rules: Iterable[ScheduleRule],
                          days_ahead: int = 14,
                          tz=None,
                          from_dt=None) -> List[dt.datetime]:
    """
    Expand weekly rules into concrete datetimes for the next N days.
    Returns a sorted list (ascending).
    """
    tz = tz or timezone.get_current_timezone()
    today = (from_dt or timezone.now()).astimezone(tz)
    start_date = today.date()

    results = []
    by_weekday = {}
    for r in rules:
        by_weekday.setdefault(r.weekday, []).append(r)

    for offset in range(days_ahead + 1):
        d = start_date + dt.timedelta(days=offset)
        wk = d.weekday()  # 0=Mon..6=Sun
        if wk not in by_weekday:
            continue
        for r in by_weekday[wk]:
            # combine date + time in TZ
            local_dt = tz.localize(dt.datetime.combine(d, r.time))
            if local_dt >= today:
                results.append(local_dt)

    results.sort()
    return results


class ClassListView(ListView):
    model = ActivityClass
    template_name = "catalog/class_list.html"
    context_object_name = "classes"
    paginate_by = 12

    def get_queryset(self):
        qs = (ActivityClass.objects
              .select_related("location", "coach")
              .prefetch_related("tags", "schedulerule_set")
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
        ctx["all_tags"] = Tag.objects.order_by("title")
        ctx["all_cities"] = (Location.objects
                             .values_list("city", flat=True)
                             .distinct().order_by("city"))

        # Next 3 occurrences per class (for cards)
        cards = []
        tz = timezone.get_current_timezone()
        for obj in ctx["classes"]:
            rules = obj.schedulerule_set.all()
            next_times = occurrences_for_rules(rules, days_ahead=14, tz=tz)[:3]
            cards.append((obj, next_times))

        ctx["cards"] = cards
        return ctx



class ClassDetailView(DetailView):
    model = ActivityClass
    slug_field = "slug"
    context_object_name = "cls"
    template_name = "catalog/class_detail.html"
    

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tz = timezone.get_current_timezone()
        # Show the next 10 upcoming sessions for this class
        rules = self.object.schedulerule_set.all()
        ctx["upcoming"] = occurrences_for_rules(rules, days_ahead=28, tz=tz)[:10]
        return ctx
