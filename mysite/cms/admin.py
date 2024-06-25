from django.contrib import admin

# Register your models here.

from .models import ShoppingListPage  # Replace with the path to your models

class ShoppingListPageAdmin(admin.ModelAdmin):
    model = ShoppingListPage
    menu_label = 'Shopping List Pages'
    menu_icon = 'list-ul'  # Choose an icon from https://docs.wagtail.io/en/stable/reference/hooks.html#register-icons
    list_display = ('title', 'live', 'first_published_at', 'last_published_at')
    search_fields = ('title',)

admin.site.register(ShoppingListPage)