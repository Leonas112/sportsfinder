from django.urls import path
from . import views

urlpatterns = [
    path('home/' , views.home_view, name='home'),
    path('search' , views.search_view, name='search'),
    
]