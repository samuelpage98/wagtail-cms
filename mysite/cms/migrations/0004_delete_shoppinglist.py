# Generated by Django 4.2.13 on 2024-06-25 12:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0003_shoppinglistpage_shoppinglist'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ShoppingList',
        ),
    ]
