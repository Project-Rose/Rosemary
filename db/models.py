from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class StarboardMessage(models.Model):
    message_id = models.CharField(max_length=19)
    starboard_message_id = models.CharField(max_length=19)
    channel_id = models.CharField(max_length=19)
    stars = models.IntegerField()
    def __str__(self):
        return str(self.message_id)

class StatusMonitor(models.Model):
    name = models.CharField(max_length=128)
    url = models.CharField(max_length=2048)
    is_down = models.BooleanField()
    downtime_start = models.DateTimeField()
    def __str__(self):
        return str(self.name)

class User(AbstractUser):
    discord_id = models.CharField(max_length=18, unique=True)
    # hacky way but idgaf!
    code = models.CharField(max_length=16, unique=True)