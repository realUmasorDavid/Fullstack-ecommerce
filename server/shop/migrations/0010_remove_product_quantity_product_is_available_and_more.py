# Generated by Django 5.1.1 on 2024-10-25 14:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0009_payment_delivery_payment_service_fee'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='quantity',
        ),
        migrations.AddField(
            model_name='product',
            name='is_available',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='sales',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]