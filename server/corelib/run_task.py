import types
import logging
from celery.app.task import Task

from kubrick.initialize import IS_DEV_ENV

logger = logging.getLogger('kubrick.celery')


class BaseTask(Task):
    """ Base Task """

    max_retries = 3
    ignore_result = False
    default_retry_delay = 5

    @property
    def name(self):
        # celery Task class must specify .name attribute ??!
        return self.__class__.__name__

    @property
    def task_desc(self):
        request_id = getattr(self.request, 'id', None)
        request_retries = getattr(self.request, 'retries', None)
        info = f'{self.name}.{request_id}.{request_retries}'
        return info

    def run(self, *args, **kwargs):
        raise NotImplementedError


class DEVBaseTask(BaseTask):
    """ 开发环境直接运行任务 """

    def run(self, *args, **kwargs):
        raise NotImplementedError

    def delay(self, *args, **kwargs):
        result = super().delay(*args, **kwargs)
        if IS_DEV_ENV:
            self.run(*args, **kwargs)
            logger.info(f'{self.task_desc} run with dev, {args} {kwargs}')
        return result


def dev_task_func_run(func, *args, **kwargs):
    """ Function task run """
    assert isinstance(func, types.FunctionType)
    task_name = func.__name__
    if IS_DEV_ENV:
        result = func(*args, **kwargs)
        logger.info(f'{task_name} has run with dev {args} {kwargs} \n {result}')
    else:
        # noinspection PyUnresolvedReferences
        task_delay = func.delay(*args, **kwargs)
        logger.info(f'{task_name}.{task_delay.id} has sent {args} {kwargs}')
    return task_name
