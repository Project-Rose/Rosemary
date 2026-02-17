from django.db import models

# Create your models here.
class StarboardMessage(models.Model):
    message_id = models.CharField(max_length=19)
    starboard_message_id = models.CharField(max_length=19)
    channel_id = models.CharField(max_length=19)
    stars = models.IntegerField()

class StatusMonitor(models.Model):
    name = models.CharField(max_length=128)
    url = models.CharField(max_length=2048)
    is_down = models.BooleanField()
    downtime_start = models.DateTimeField()

class BannedPhrase(models.Model):
    phrase = models.CharField(max_length=255, unique=True)
    added_by = models.CharField(max_length=19)
