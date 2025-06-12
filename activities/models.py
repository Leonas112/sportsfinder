from django.db import models

# Create your models here.

class Activity(models.Model):
    title       = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    coach       = models.TextField()
    price       = models.TextField()
    location    = models.TextField(default="cool")