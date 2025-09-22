import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from catalog.models import ActivityClass, Location, Booking
from catalog.utils import make_occurrence_token

User = get_user_model()


@pytest.mark.django_db
def test_booking_flow(client):
    # setup
    u = User.objects.create_user("leo", "leo@example.com", "pass")
    loc = Location.objects.create(city="Kaunas", address1="Main St")
    ac = ActivityClass.objects.create(title="Yoga", slug="yoga", location=loc)
    start = timezone.now() + datetime.timedelta(days=1, hours=1)
    end = start + datetime.timedelta(hours=1)
    token = make_occurrence_token(ac.id, start, end)

    # must login
    url = reverse("class-book", args=[ac.slug])
    r = client.post(url, {"token": token})
    assert r.status_code == 302  # redirected to login or detail

    client.login(username="leo", password="pass")

    # create
    r = client.post(url, {"token": token}, follow=True)
    assert r.status_code == 200
    assert Booking.objects.filter(user=u, activity_class=ac, start=start).exists()

    # duplicate
    r = client.post(url, {"token": token}, follow=True)
    assert Booking.objects.filter(user=u, activity_class=ac, start=start).count() == 1
