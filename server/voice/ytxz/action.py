"""
https://console.ytx.net/FileDetails/FileAccessGuide
"""
import time
import base64
import logging
from json import JSONDecodeError
from abc import ABC, abstractmethod
from sentry_sdk import configure_scope, capture_message, capture_exception

from server.constant import mochoice as mc
from server.corelib.utils.req_retry import get_retry_session
from server.corelib.sequence.idshift import generate_uuid5, hash_md5
from server.corelib.dealer.deal_time import get_now
from . import ytx_const as const

logger = logging.getLogger('kubrick.api')


class YTXReqAction(ABC):
    """ YTX云讯接口请求 """

    provider = mc.ThirdProvider.YTX
    _request = get_retry_session()

    def __init__(self, **params):
        self._ts = round(1000 * time.time())
        self._ruid = generate_uuid5().hex
        self._params = params

    @property
    @abstractmethod
    def action(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def apipath(self):
        raise NotImplementedError

    @property
    def url(self):
        return f'{const.REST_URL}{self.apipath}'

    @property
    def req_extra(self):
        extra = dict(
            action=self.action,
            apipath=self.apipath,
        )
        return extra

    def sentry_capture(self, msg, exc, **extra):
        capture_exception(exc)
        exc_type = type(exc).__name__
        extra_all = {**self.req_extra, **dict(exc=exc_type), **extra}
        with configure_scope() as scope:
            for k, v in extra_all.items():
                scope.set_extra(k, v)
            scope.set_extra('ruid', self._ruid)
            scope.set_tag('cloud_service ', self.provider)
            capture_message(msg, level='warning')
            capture_exception(error=exc)
        logger.warning(f'ytx__{self.action} {msg} {self._ruid}: {extra_all}')
        logger.exception(msg)

    def ytx_req_count(self, result_type):
        from server.applibs.monitor.models import CountThirdApi
        ts_use = round(1000 * time.time()) - self._ts
        logger.info(f'ytx_req_count__use_ms__{self.action} {self._ruid} {ts_use}')
        inst = CountThirdApi.objects.count_thirdapi_increase(
            self.provider, self.action,
            result_type=result_type,
            use_ms=ts_use,
        )
        return inst

    def do_action(self):
        now = get_now()
        now_str = now.format('YYYYMMDDHHmmss')
        sign = hash_md5(f'{const.ACCOUNT_SID}{const.AUTH_TOKEN}{now_str}')
        authorization = base64.b64encode(f'{const.ACCOUNT_SID}|{now_str}'.encode()).decode()
        headers = {
            'Accept': 'application/json;',
            'Content-Type': 'application/json;charset=utf-8;',
            'Authorization': authorization,
        }
        resp_dic = self._request.post(
            self.url, json=self._params,
            params=dict(Sign=sign),
            headers=headers,
        ).json()
        return resp_dic

    def do_action_with_try(self):
        logger.info(f'ytx_action__req__{self.action} {self._ruid} {self.req_extra}')
        try:
            resp_dic = self.do_action()
            assert isinstance(resp_dic, dict)
            logger.info(f'ytx_action__resp_done {self.action} {self._ruid}')
        except (AssertionError, JSONDecodeError) as exc:
            self.sentry_capture('resp__error', exc)
            self.ytx_req_count(mc.ThirdResultType.RespExc)
            raise exc
        except Exception as exc:
            self.sentry_capture('req__exc', exc)
            self.ytx_req_count(mc.ThirdResultType.ReqExc)
            raise exc
        return resp_dic

    def resp_check(self, resp_dic: dict):
        """ 结果检查 """
        raise NotImplementedError

    def fetch_result(self):
        """ 返回内容检查是否成功 """
        resp_dic = self.do_action_with_try()
        try:
            result = self.resp_check(resp_dic)
        except (KeyError, AssertionError) as exc:
            self.sentry_capture('resp__failure', exc)
            self.ytx_req_count(mc.ThirdResultType.RespFail)
            logger.warning(f'resp_check__fail__{self.action} {self._ruid} {resp_dic}')
            exc_str = resp_dic.get('statusMsg') or resp_dic.get('statusCode') or '未知异常'
            raise Exception(exc_str)
        self.ytx_req_count(mc.ThirdResultType.Success)
        return result
