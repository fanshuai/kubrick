"""
django-silk
https://pypi.org/project/django-silk/
"""
import random
import logging

from kubrick.initialize import (
    IS_PROD_ENV, IS_DEV_ENV,
    IS_DJADMIN, SILKY_DIR,
)

logger = logging.getLogger('kubrick.debug')


def is_superuser_func(user):
    return getattr(user, 'is_superuser', False)


def silky_custom_logic_func(request):
    if '/favicon.ico' in request.path:
        return False
    if IS_DEV_ENV:
        return False  # DEV 0%
    if IS_DJADMIN:
        return False  # Djadmin 0%
    if not IS_PROD_ENV:
        is_silky = random.randint(1, 20) == 1  # SIT 5%
    elif getattr(request.user, 'is_staff', False):
        is_silky = random.randint(1, 50) == 1  # 线上员工用户 2%
    else:
        is_silky = random.randint(1, 100) == 1  # 线上普通用户 1%
    path, usrid = request.path, request.user.pk
    logger.info(f'silky_custom_logic_func__result {path} {usrid}: {is_silky}')
    return is_silky


SILKY_META = False
SILKY_AUTHENTICATION = True  # User must login
SILKY_AUTHORISATION = True  # User must have permissions
SILKY_PERMISSIONS = is_superuser_func
SILKY_INTERCEPT_FUNC = silky_custom_logic_func
SILKY_PYTHON_PROFILER_RESULT_PATH = SILKY_DIR
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_PYTHON_PROFILER = True
