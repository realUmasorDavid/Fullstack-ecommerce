# Generated by Django 5.1.1 on 2024-10-25 18:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0010_remove_product_quantity_product_is_available_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_rider',
            field=models.BooleanField(default=False),
        ),
    ]
