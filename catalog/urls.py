from django.urls import path
from .views import ClassListView, ClassDetailView

app_name = "catalog"

urlpatterns = [
    path("classes/", ClassListView.as_view(), name="class_list"),
    path("classes/<slug:slug>/", ClassDetailView.as_view(), name="class_detail"),
]
