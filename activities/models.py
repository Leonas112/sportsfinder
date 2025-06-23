from django.db import models
from django.conf import settings

# Create your models here.

class Activity(models.Model):
    title       = models.CharField(max_length=120)
    description = models.TextField()
    category    = models.CharField(max_length=50)
    contacts    = models.TextField()
    location    = models.CharField(max_length=120)
    owner       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.title