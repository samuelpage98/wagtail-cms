from django.contrib import admin
# from admin_commands.models import ManagementCommands

# Register your models here.

from .models import Topic, Entry

admin.site.register(Topic)
admin.site.register(Entry)
# admin.site.register(ManagementCommands)
