# Generated by Django 5.1.1 on 2024-10-01 09:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0010_remove_order_items_remove_order_total_amount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='delivered',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
    ]
