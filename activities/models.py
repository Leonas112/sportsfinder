from django.db import models

# Create your models here.

class Activity(models.Model):
    title       = models.TextField()
    description = models.TextField()
    coach       = models.TextField()
    price       = models.TextField()
    location    = models.TextField(default="cool")