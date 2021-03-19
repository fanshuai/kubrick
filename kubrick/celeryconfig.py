"""
Celery Tasker Config

http://docs.celeryproject.org/en/latest/userguide/routing.html
http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
"""
# from kombu import Queue

from kubrick.initialize import CONFIG
from server.constant.djalias import CQueueAlias

broker_url = CONFIG('CELERY.BROKER_URL')

result_backend = 'django-db'
task_default_queue = CQueueAlias.Default.value
# task_queues = (
#     Queue(name=CQueueAlias.Default.value, routing_key='default'),
#     Queue(name=CQueueAlias.Timed.value, routing_key='timed.#'),
# )
# task_routes = ([
#     # ('server.applibs.tasks.*', {'queue': CQueueAlias.Timed.value}),
# ],)

task_time_limit = 60 * 60
# resolve celery does not release memory

task_ignore_result = False

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']

timezone = 'Asia/Shanghai'


imports = (
    'server.corelib.notice.async_tasks',
)
