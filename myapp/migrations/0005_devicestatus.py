# Generated by Django 5.2.1 on 2025-06-24 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_userprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(max_length=100, unique=True)),
                ('status', models.CharField(max_length=10)),
                ('mode', models.CharField(max_length=10)),
                ('last_active', models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
