import time
import logging
from functools import wraps
from sentry_sdk import capture_exception
from django.db import connection, connections

logger = logging.getLogger('kubrick.debug')


def retry(retries=2):
    """ 重试逻辑 """
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tried = 0
            while tried < retries:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    logger.warning(f'retry {func.__name__} {tried} error {str(exc)}')
                    logger.exception(str(exc))
                    capture_exception(exc)
                    tried += 1
                    time.sleep(100 * tried)
            else:
                raise RuntimeError(f'retry {func.__name__} {tried}/{retries}')
        return wrapper
    return deco


def sentry_try(func):
    """ Sentry Try 异常并抛出 """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logging.exception(str(exc))
            capture_exception(exc)
            raise
    return wrapper


def sentry_catch(func):
    """ Sentry Catch 异常并忽略 """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logging.exception(str(exc))
            capture_exception(exc)
    return wrapper


def sentry_catch_ret(default=None):
    """ Sentry Catch 异常并忽略，返回默认返回值 """
    def deco(func):
        """ Sentry Catch 异常并忽略 """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                logging.exception(str(exc))
                capture_exception(exc)
                return default
        return wrapper
    return deco


def auto_close_db(f):
    """
    Ensures the database connection is closed when the function returns.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        finally:
            connection.close()
            for conn in connections.all():
                conn.close_if_unusable_or_obsolete()
    return wrapper
