from celery import Celery

app = Celery('GEMA')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Use the Django database as the beat schedule store
app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'
