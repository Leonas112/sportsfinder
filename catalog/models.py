from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.utils.text import slugify
from django.urls import reverse

class Location(models.Model):
    # Optional nickname; can help if an address is long
    # name = models.CharField(max_length=120, blank=True)
    address1 = models.CharField(max_length=200, null = True)
    address2 = models.CharField(max_length=200, null = True, blank=True)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=60, default="")


    slug = models.SlugField(max_length=160, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Prefer a compact slug based on address/city
            base = self.name or f"{self.address1}-{self.city}"
            self.slug = slugify(base)[:150]
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name or f"{self.address1}, {self.city}"
    
class Coach(models.Model):
    # Either link to a real user, or just type a name
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="coaching_profiles",
    )
    name = models.CharField(max_length=120, blank=True)

    def clean(self):
        if not self.user and not self.name:
            raise ValidationError("Provide either a linked user or a name for the coach.")

    @property
    def display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.name

    def __str__(self):
        return self.display_name

    
class Tag(models.Model):
    name = models.CharField(max_length = 40, unique=True)
    slug = models.SlugField(max_length = 50, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug=slugify(self.name)
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class ActivityClass(models.Model):
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="classes")
    coach = models.ForeignKey(Coach, on_delete=models.SET_NULL, null=True, blank=True, related_name="classes")
    price = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    tags = models.ManyToManyField(Tag, blank=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = f"{self.title}-{self.location.city}"
            self.slug = slugify(base)[:150]
        return super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse("class-detail", args=[self.slug])

    def __str__(self):
        return self.title
    


class ScheduleRule(models.Model):
    """Weekly recurrence rule: e.g. Mon & Wed @ 17:30 from start_date → end_date."""
    MON, TUE, WED, THU, FRI, SAT, SUN = range(7)
    WEEKDAY_CHOICES = (
        (MON, "Mon"), (TUE, "Tue"), (WED, "Wed"), (THU, "Thu"),
        (FRI, "Fri"), (SAT, "Sat"), (SUN, "Sun"),
    )

    activity_class = models.ForeignKey(ActivityClass, on_delete=models.CASCADE, related_name="weekly_rules")
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, null = True)
    time = models.TimeField(null = True, blank = True)                   # 17:30
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(null=True, blank=True)  # optional open-ended
    interval = models.PositiveIntegerField(default=1)   # every N weeks
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["activity_class", "weekday", "time"]

    def __str__(self):
        return f"{self.get_weekday_display()} {self.time} · {self.activity_class}"

    # Convenience to produce upcoming dates (for list/detail)
    def next_occurrences(self, count=8, from_date=None):
        """Generate the next N dates this rule applies to (without times)."""
        from_date = from_date or date.today()
        # find the next weekday on/after from_date
        days_ahead = (self.weekday - from_date.weekday()) % 7
        current = from_date + timedelta(days=days_ahead)
        generated = []

        while len(generated) < count:
            if (not self.end_date) or (current <= self.end_date):
                if self.active and current >= self.start_date:
                    generated.append(current)
            current += timedelta(weeks=self.interval)

        return generated
