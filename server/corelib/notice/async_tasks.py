"""
异步通知任务
"""
import logging

from kubrick.celery import app
from server.corelib.run_task import BaseTask

logger = logging.getLogger('kubrick.celery')


class AliMailSendTask(BaseTask):
    """ 阿里云[邮件]异步任务发送 """

    def run(self, tos, subject, content, *args, **kwargs):
        try:
            result = self.mail_send(tos, subject, content)
        except Exception as exc:
            exc_name = exc.__class__.__name__
            retries = self.request.retries + 1
            print(f'##### {self.task_desc} exc:{exc_name} retry:{retries} ...')
            raise self.retry(exc=exc)
        return result

    def mail_send(self, tos, subject='', content=''):
        """
        :param tos: 收件人列表(英文逗号分隔)
        :param subject: 邮件主题
        :param content: 邮件内容
        :return:
        """
        from server.corelib.notice.send_mail import send_mail_msg
        logger.info(f'Executing {self.task_desc} start {tos} {subject} ...')
        ret = send_mail_msg(to=tos, subject=subject, html_body=content, text_body=content)
        logger.info(f'Executing {self.task_desc} done.')
        result = dict(task=self.name, task_info=self.task_desc, ret=ret)
        return result


class AliDDSendTask(BaseTask):
    """ 阿里云[钉钉]报警异步任务发送 """

    def run(self, content='', *args, **kwargs):
        try:
            result = self.dingding_send(content)
        except Exception as exc:
            exc_name = exc.__class__.__name__
            retries = self.request.retries + 1
            print(f'##### {self.name}.{self.request.id} exc:{exc_name} retry:{retries} ...')
            raise self.retry(exc=exc)
        return result

    def dingding_send(self, content, at_mobiles=None, is_atall=False):
        """
        :param content: 消息内容
        :param at_mobiles: @某人
        :param is_atall: @所有人
        :return:
        """
        from server.corelib.notice.send_dd import send_dd_msg
        logger.info(f'Executing {self.task_desc} start ... \n##### [{content}] [{at_mobiles}] [{is_atall}]')
        is_succ, msg = send_dd_msg(content, at_mobiles=at_mobiles, is_atall=is_atall)
        assert is_succ, f'alarm_dingding_send__fail {self.task_desc}'
        logger.info(f'Executing {self.task_desc} done. \n##### [is_succ:{is_succ}] [msg:{msg}]')
        result = dict(task=self.name, is_succ=is_succ, msg=msg)
        return result


def send_dd_msg__task(content=''):
    """ [钉钉] 发送报警信息 """
    task_dd = AliDDSendTask()
    task_dd_delay = task_dd.delay(content)
    logger.info(f'send_dd_msg__task__done {task_dd.name}.{task_dd_delay.id} has_sent:\n{content}')


app.tasks.register(AliDDSendTask())
app.tasks.register(AliMailSendTask())
