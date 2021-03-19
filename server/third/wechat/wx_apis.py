"""
微信小程序API
https://developers.weixin.qq.com/miniprogram/dev/api-backend/
"""
import logging
import requests

from server.constant import mochoice as mc
from server.third.wechat.action import WXReqAction

logger = logging.getLogger('kubrick.api')


class WXAccessToken(WXReqAction):
    """
    auth.getAccessToken  获取小程序全局唯一后台接口调用凭据（access_token）。
    """

    allow_cache = True
    action = mc.ThirdAction.WXAccessToken
    apipath = '/cgi-bin/token'

    def do_action(self):
        params = dict(
            grant_type='client_credential',
            appid=self.appid, secret=self.secret,
        )
        resp_dic = self._request.get(self.url, params=params).json()
        return resp_dic

    def resp_check_and_cache(self, resp_dic: dict):
        access_token = resp_dic['access_token']
        expires_in = resp_dic['expires_in']
        assert access_token and expires_in
        if self.cachekey and expires_in > 0:
            self._cache_timeout = round(expires_in * 9 / 10)
        else:
            self._cache_timeout = 0
        return access_token


class WXCodeSession(WXReqAction):
    """
    auth.code2Session 登录凭证校验。
    """

    allow_cache = False
    action = mc.ThirdAction.WXCodeSession
    apipath = '/sns/jscode2session'

    def do_action(self):
        params = dict(
            appid=self.appid,
            secret=self.secret,
            js_code=self._params['code'],
            grant_type='authorization_code',
        )
        # {'errcode': 40163, 'errmsg': 'code been used ...'}
        resp_dic = requests.get(self.url, params=params).json()  # 不重试
        logger.info(f'=== WXCodeSession.debug === {self.action} {self.apipath} \n{resp_dic}')
        return resp_dic

    def resp_check_and_cache(self, resp_dic: dict):
        """
        百分百能获得unionid的只有wx.getUserInfo解密
        https://developers.weixin.qq.com/community/develop/doc/00080ea95b82301b2929e1e5d56800
        """
        logger.info(f'=== WXCodeSession.resp_check_and_cache === {self.action} {self.apipath} \n{resp_dic}')
        assert 'session_key' in resp_dic, resp_dic.get('errmsg', '')
        assert 'openid' in resp_dic, resp_dic.get('errmsg', '')
        session_key = resp_dic['session_key']
        openid = resp_dic['openid']
        assert (openid and session_key), resp_dic
        result = openid, session_key
        return result


class WXPaidUnionId(WXReqAction):
    """
    auth.getPaidUnionId 获取支付UnionId。
    """

    allow_cache = True
    action = mc.ThirdAction.WXPaidUnionId
    apipath = '/wxa/getpaidunionid'

    def do_action(self):
        access_token = WXAccessToken().get_result()
        params = dict(access_token=access_token, openid=self._params['openid'])
        resp_dic = self._request.get(self.url, params=params).json()
        return resp_dic

    def resp_check_and_cache(self, resp_dic: dict):
        unionid = resp_dic['unionid']
        return unionid


class WXMsgSecCheck(WXReqAction):
    """
    security.msgSecCheck 内容安全文本违规。
    """

    allow_cache = True
    action = mc.ThirdAction.WXMsgSecCheck
    apipath = '/wxa/msg_sec_check'

    def do_action(self):
        access_token = WXAccessToken().get_result()
        data = dict(content=self._params['content'])
        params = dict(access_token=access_token)
        resp_dic = self._request.post(self.url, json=data, params=params).json()
        return resp_dic

    def resp_check_and_cache(self, resp_dic: dict):
        errcode = resp_dic['errcode']
        errmsg = resp_dic['errmsg']
        is_ok = errcode == 0
        result = is_ok, errcode, errmsg
        return result


class WXSubscribeMessage(WXReqAction):
    """
    subscribeMessage.send 发送订阅消息。
    """

    allow_cache = False
    action = mc.ThirdAction.WXSubscribeSend
    apipath = '/cgi-bin/message/subscribe/send'

    def do_action(self):
        access_token = WXAccessToken().get_result()
        params = dict(access_token=access_token)
        resp_dic = self._request.post(self.url, json=self._params, params=params).json()
        return resp_dic

    def resp_check_and_cache(self, resp_dic: dict):
        return resp_dic
