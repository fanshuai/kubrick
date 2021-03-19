# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration

from .celery import app as celery_app
from kubrick.initialize import (
    VERSION, RUN_ENV, HOST_NAME, SENTRY_DSN
)

ignore_logger('django.security.DisallowedHost')

# https://sentry.io/for/python/
sentry_sdk.init(
    dsn=SENTRY_DSN,
    release=VERSION,
    environment=RUN_ENV,
    server_name=HOST_NAME,
    ignore_errors=[
        KeyboardInterrupt,
    ],
    integrations=[
        RedisIntegration(),
        CeleryIntegration(),
        DjangoIntegration(),
        TornadoIntegration(),
    ]
)


__all__ = ['celery_app']
