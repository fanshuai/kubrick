import os
import celery
import logging

logger = logging.getLogger('kubrick.celery')

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kubrick.settings')
os.environ.setdefault('CELERY_CONFIG_MODULE', 'kubrick.celeryconfig')

# Sentry: https://sentry.io/for/celery/
app = celery.Celery('kubrick')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
# app.config_from_object('django.conf:settings', namespace='CELERY')
app.config_from_envvar('CELERY_CONFIG_MODULE')

# http://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html
app.conf.broker_transport_options = {'visibility_timeout': 3600}  # 1 hour.

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# # app.conf.beat_schedule by django_celery_beat
# http://localhost/__admin/django_celery_beat/periodictask/


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


if __name__ == '__main__':
    import django
    django.setup()
    app.start()
