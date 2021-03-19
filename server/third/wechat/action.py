import time
import hashlib
import logging
from json import JSONDecodeError
from dataclasses import dataclass
from abc import ABC, abstractmethod
from django.core.cache import cache
from sentry_sdk import configure_scope, capture_message, capture_exception

from server.constant import mochoice as mc
from server.corelib.utils.req_retry import get_retry_session
from server.corelib.sequence.idshift import generate_uuid5

logger = logging.getLogger('kubrick.api')


@dataclass
class ASConfig:
    """ 凭证配置 """
    appid: str
    secret: str


as_cfg = ASConfig(
    appid='appid...',
    secret='secret...',
)


class WXReqAction(ABC):
    """ 微信接口请求 """

    allow_cache = False
    appid = as_cfg.appid
    secret = as_cfg.secret

    provider = mc.ThirdProvider.Wechat
    _cache_timeout = 60 * 5
    _request = get_retry_session()
    _cache = cache

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
        return f'https://api.weixin.qq.com{self.apipath}'

    @property
    def cachekey(self):
        if not self.allow_cache:
            return None
        items = f'{self.apipath}'
        for p in sorted(self._params):
            pv = self._params[p]
            if p in ['content']:
                if not isinstance(pv, str):
                    return None  # 不缓存
                # 长内容以MD5摘要为Key缓存
                pv_hash = hashlib.md5(pv.encode()).hexdigest()
                val = f'md5[{pv_hash}]'
            else:
                val = self._params[p]
            items += f';{p}:{val}'
        items_hash = hashlib.sha1(items.encode()).hexdigest()
        key = f'wx:{self.action}:{items_hash}'
        return key

    @property
    def req_extra(self):
        extra = dict(
            action=self.action,
            apipath=self.apipath,
            cachekey=self.cachekey,
        )
        return extra

    def sentry_capture(self, msg, exc, **extra):
        capture_exception(exc)
        exc_type = type(exc).__name__
        extra_all = {**self.req_extra, **dict(exc=exc_type), **extra}
        with configure_scope() as scope:
            scope.set_tag('cloud_service ', self.provider)
            for k, v in extra_all.items():
                scope.set_extra(k, v)
            scope.set_extra('ruid', self._ruid)
            capture_message(msg, level='warning')
            capture_exception(error=exc)
        logger.warning(f'wechat__{self.action} {msg} {self._ruid}: {extra_all}')
        logger.exception(msg)

    def wechat_req_count(self, result_type):
        from server.applibs.monitor.models import CountThirdApi
        ts_use = round(1000 * time.time()) - self._ts
        logger.info(f'wechat_req_count__use_ms__{self.action} {self._ruid} {ts_use}')
        inst = CountThirdApi.objects.count_thirdapi_increase(
            self.provider, self.action,
            result_type=result_type,
            use_ms=ts_use,
        )
        return inst

    def do_action(self):
        raise NotImplementedError

    def do_action_with_try(self):
        logger.info(f'wechat_action__req__{self.action} {self._ruid} {self.req_extra}')
        try:
            resp_dic = self.do_action()
            assert isinstance(resp_dic, dict)
        except (AssertionError, JSONDecodeError) as exc:
            self.sentry_capture('resp__error', exc)
            self.wechat_req_count(mc.ThirdResultType.RespExc)
            raise exc
        except Exception as exc:
            self.sentry_capture('req__exc', exc)
            self.wechat_req_count(mc.ThirdResultType.ReqExc)
            raise exc
        return resp_dic

    def resp_check_and_cache(self, resp_dic: dict):
        """ 结果检查及缓存 """
        raise NotImplementedError

    def resp_check_and_cache_with_try(self):
        """ 返回内容检查是否成功 """
        resp_dic = self.do_action_with_try()
        try:
            result = self.resp_check_and_cache(resp_dic)
        except (KeyError, AssertionError) as exc:
            self.sentry_capture('resp__failure', exc)
            self.wechat_req_count(mc.ThirdResultType.RespFail)
            logger.warning(f'resp_check_and_cache_with_try__fail__{self.action} {self._ruid} {resp_dic}')
            raise exc
        self.wechat_req_count(mc.ThirdResultType.Success)
        return result

    def get_cache_result(self):
        """ 获取缓存数据 """
        if not self.cachekey:
            return None
        result = self._cache.get(self.cachekey)
        if not result:
            return None
        ttl = self._cache.ttl(self.cachekey)
        logger.info(f'wxapi_result_cache_get_ok {self.cachekey} {ttl}')
        return result

    def set_cache_result(self, result):
        """ 更新缓存数据 """
        if not (self.cachekey and result and self._cache_timeout > 0):
            return None
        self._cache.set(self.cachekey, result, timeout=self._cache_timeout)
        logger.info(f'wxapi_result_cache_set_ok {self.cachekey} {self._cache_timeout}')
        return result

    def get_result(self):
        result = self.get_cache_result()
        if result:
            return result
        result = self.resp_check_and_cache_with_try()
        self.set_cache_result(result)
        return result
