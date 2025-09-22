from django.urls import path
from . import views

urlpatterns = [
    path("classes/", views.ActivityClassList.as_view(), name="class-list"),
    path("classes/<slug:slug>/book/", views.book_session, name="class-book"),
    path("classes/<slug:slug>/", views.ActivityClassDetail.as_view(), name="class-detail"),
]
