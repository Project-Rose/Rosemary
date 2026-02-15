from django.db import models

# Create your models here.
class StarboardMessage(models.Model):
    message_id = models.CharField(max_length=19)
    starboard_message_id = models.CharField(max_length=19)
    channel_id = models.CharField(max_length=19)
    stars = models.IntegerField()