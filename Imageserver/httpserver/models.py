from django.db import models
from django import forms

class Image(models.Model):
    image = models.FileField(upload_to='images/')
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    os = models.CharField(max_length=200)
    version = models.CharField(max_length=200)
    size = None

    def __str__(self):
        return self.version