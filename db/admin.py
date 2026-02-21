from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin
from .models import *

admin.site.register(StarboardMessage)
admin.site.register(StatusMonitor)
admin.site.register(User)
admin.site.register(WikiPage, MarkdownxModelAdmin)