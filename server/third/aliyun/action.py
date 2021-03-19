import json
import time
import logging
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import AcsRequest
from sentry_sdk import configure_scope, capture_message, capture_exception

from server.constant import mochoice as mc
from server.corelib.sequence.idshift import generate_uuid5

logger = logging.getLogger('kubrick.api')


class AliReqAction(object):
    """ 阿里云接口请求 """

    provider = mc.ThirdProvider.Aliyun

    def __init__(self, request, client=None):
        if not client:
            from .access import acs_client
            client = acs_client
        assert isinstance(client, AcsClient)
        assert isinstance(request, AcsRequest)
        request.set_accept_format('JSON')
        request.set_connect_timeout(2)
        request.set_read_timeout(6)
        self._ts = round(1000 * time.time())
        self._ruid = generate_uuid5().hex
        self._request = request
        self._client = client

    @property
    def region(self):
        return self._client.get_region_id()

    @property
    def action(self):
        return self._request.get_action_name()

    @property
    def version(self):
        return self._request.get_version()

    @property
    def uri_pattern(self):
        return self._request.get_uri_pattern()

    @property
    def req_content(self):
        return self._request.get_content()

    @property
    def req_extra(self):
        extra = dict(
            action=self.action,
            region=self.region,
            version=self.version,
            uri_pattern=self.uri_pattern,
        )
        return extra

    def sentry_capture(self, msg, exc, **extra):
        capture_exception(exc)
        exc_type = type(exc).__name__
        extra_all = {**self.req_extra, **dict(exc=exc_type), **extra}
        with configure_scope() as scope:
            scope.set_tag('cloud_service ', self.provider)
            scope.set_tag('aliyun_action', self.action)
            for k, v in extra_all.items():
                scope.set_extra(k, v)
            scope.set_extra('ruid', self._ruid)
            capture_message(msg, level='warning')
            capture_exception(error=exc)
        logger.warning(f'aliyun__{self.action} {msg} {self._ruid}: {extra_all}')
        logger.exception(msg)

    def aliyun_req_count(self, result_type):
        from server.applibs.monitor.models import CountThirdApi
        ts_use = round(1000 * time.time()) - self._ts
        logger.info(f'aliyun_req_count__use_ms__{self.action} {self._ruid} {ts_use}')
        inst = CountThirdApi.objects.count_thirdapi_increase(
            self.provider, self.action,
            result_type=result_type,
            use_ms=ts_use,
        )
        return inst

    def do_action_with_try(self):
        logger.info(f'aliyun_action__req__{self.action} {self._ruid} {self.req_extra} {self.req_content}')
        try:
            response = self._client.do_action_with_exception(self._request)
        except Exception as exc:
            self.sentry_capture('req__exc', exc)
            self.aliyun_req_count(mc.ThirdResultType.ReqExc)
            logger.warning(f'aliyun_action__resp__{self.action} {self._ruid} error: {str(exc)}')
            raise exc
        else:
            response = str(response, encoding='utf-8')
            logger.info(f'aliyun_action__resp__{self.action} {self._ruid} success')
        return response

    def response_loads(self, response: str) -> dict:
        try:
            resp_dic = json.loads(response)
        except Exception as exc:
            exc_type = type(exc).__name__
            self.sentry_capture('resp__error', exc)
            self.aliyun_req_count(mc.ThirdResultType.RespExc)
            resp_dic = dict(memo='resp__error', response=response, ruid=self._ruid, exc=exc_type)
        else:
            self.response_check_ok(resp_dic)
        return resp_dic

    def response_check_ok(self, resp_dic: dict):
        """ 返回内容检查是否成功 """
        try:
            if self.action == mc.ThirdAction.ALISendSms:  # 短信服务: 发送短信
                assert resp_dic['RequestId']
                assert resp_dic['Message'] == 'OK'
                assert resp_dic['Code'] == 'OK'
                assert 'BizId' in resp_dic
            elif self.action == mc.ThirdAction.ALISingleSendMail:  # 邮件推送: 单一发信接口
                assert resp_dic['RequestId']
                assert resp_dic['EnvId']
            elif self.action in [
                mc.ThirdAction.ALIImageSyncScan,  # 图片OCR识别
                mc.ThirdAction.ALITextScan,  # 文本反垃圾
            ]:  # 内容安全
                assert resp_dic['requestId']
                assert resp_dic['msg'] == 'OK'
                assert resp_dic['code'] == 200
            else:
                logger.info(f'response_check_ok__ignore__{self.action} {self._ruid} {resp_dic}')
        except (KeyError, AssertionError) as exc:
            self.sentry_capture('resp__failure', exc)
            self.aliyun_req_count(mc.ThirdResultType.RespFail)
            logger.warning(f'response_check_ok__fail__{self.action} {self._ruid} {resp_dic}')
        else:
            self.aliyun_req_count(mc.ThirdResultType.Success)

    def do_req_action(self) -> dict:
        response = self.do_action_with_try()
        resp_dic = self.response_loads(response)
        return resp_dic
