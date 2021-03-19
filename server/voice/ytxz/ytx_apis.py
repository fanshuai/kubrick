"""
云讯：
    早八晚八禁用
    单号码并发15路通话
"""
import logging

from server.constant import mochoice as mc
from . import ytx_const as const
from .action import YTXReqAction

logger = logging.getLogger('kubrick.api')


class YTXDailBackCallApi(YTXReqAction):
    """ 双向呼叫
    https://console.ytx.net/FileDetails/FileDailBackCall

    {'statusCode': '0', 'statusMsg': '提交成功', 'requestId': '20200437755840048670965760400'}
    """
    action = mc.ThirdAction.YTXCallDailBack
    apipath = f'/201512/sid/{const.ACCOUNT_SID}/call/DailbackCall.wx'

    def __init__(self, src, dst, callid):
        params = dict(
            src=src, dst=dst,
            customParm=callid,
            appid=const.YTX_APPID,
            action='callDailBack',
            srcclid=const.YTX_SHOW_NUM,  # 第一端外显号码
            dstclid=const.YTX_SHOW_NUM,  # 第二端外显号码
            srctimeout=30,  # 设置第一路电话超时时间 以秒为单位（超过时间第一路挂断）
            dsttimeout=50,  # 设置第二路电话超时时间 以秒为单位（超过时间第二路挂断）
            credit=60 * 3,  # 三分钟，通话时长限制，单位为秒，必须大于60
        )
        super().__init__(**params)

    def resp_check(self, resp_dic: dict):
        assert resp_dic['statusCode'] == '0'
        assert resp_dic['requestId']
        return resp_dic


class YTXQueryBlanceApi(YTXReqAction):
    """ 查询余额
    https://console.ytx.net/FileDetails/FileGetBlance

    {'AccountSID': 'ee76c8fe84364a5f8623bc4528debe30', 'Blance': 7.08}
    """
    action = mc.ThirdAction.YTXQueryBlance
    apipath = f'/201612/sid/{const.ACCOUNT_SID}/account/getBlance.wx'

    def __init__(self):
        params = dict(
            appid=const.YTX_APPID,
            action='queryBlance',
        )
        super().__init__(**params)

    def resp_check(self, resp_dic: dict):
        print('>' * 22)
        print(self.action)
        print(resp_dic)
        print('>' * 22)
        return resp_dic


class YTXCallCdrByResIdApi(YTXReqAction):
    """ 话单获取，增量方式话单
    https://console.ytx.net/FileDetails/FileGetCallCdr

    {'cdr': [{'requestid': '20200437752594783293931520401',
   'appid': 'ff1f324a0604417c9c7f5f1186225fda',
   'fid': 4,
   'caller': '18610559223',
   'called': '18612035220',
   'callerstime': '2020-04-27 17:33:32',
   'calleretime': '2020-04-27 17:33:46',
   'calledstime': '',
   'calledetime': '2020-04-27 17:33:46',
   'tapesurl': 'NoTapes',
   'duration': 14,
   'oriamount': 0.15,
   'customParm': '',
   'stateDesc': '应答|正常'}]}
    """
    action = mc.ThirdAction.YTXCallCdr
    apipath = f'/201512/sid/{const.ACCOUNT_SID}/call/CallCdr.wx'

    def __init__(self, lastresid='0', limit=1):
        params = dict(
            limit=limit,  # 如果limit=0，表示获取requestid=lastresid的一条话单
            lastresid=lastresid,  # 若是第一次获取话单则lastresid="0",此时limit不能为0。
            appid=const.YTX_APPID,
            action='getCdrByResId',  # 增量方式话单
            fid='4',  # 语音类接口功能编号：双向呼叫（fid="4"）
        )
        super().__init__(**params)

    def resp_check(self, resp_dic: dict):
        assert isinstance(resp_dic['cdr'], list)
        return resp_dic


class YTXCallCdrByResIdOneApi(YTXCallCdrByResIdApi):
    """ 话单获取，增量方式话单，获取当前单个话单 """
    def __init__(self, lastresid):
        super().__init__(lastresid=lastresid, limit=0)
        self.lastresid = lastresid

    def resp_check(self, resp_dic: dict):
        try:
            assert isinstance(resp_dic['cdr'], list)
            one_dic = resp_dic['cdr'][0]
            assert isinstance(one_dic, dict)
            assert one_dic['requestid'] == self.lastresid
        except (KeyError, AssertionError):
            logger.warning(f'{self.__class__.__name__}.resp_wrong {self.lastresid}: {resp_dic}')
            return None
        return one_dic


class YTXCallCdrByTimeApi(YTXCallCdrByResIdApi):
    """ 话单获取，某小时话单
    https://console.ytx.net/FileDetails/FileGetCallCdr

   {'cdr': [{'requestid': '20200437755796137831301120400',
   'appid': 'ff1f324a0604417c9c7f5f1186225fda',
   'fid': 4,
   'caller': '18610559223',
   'called': '18612035220',
   'callerstime': '2020-04-28 14:45:42',
   'calleretime': '2020-04-28 14:45:58',
   'calledstime': '',
   'calledetime': '2020-04-28 14:45:58',
   'tapesurl': 'NoTapes',
   'duration': 16,
   'oriamount': 0.15,
   'customParm': 'order-id-123456'},
  {'requestid': '20200437755811196850667520400',
   'appid': 'ff1f324a0604417c9c7f5f1186225fda',
   'fid': 4,
   'caller': '18610559223',
   'called': '01053189990',
   'callerstime': '2020-04-28 14:51:37',
   'calleretime': '2020-04-28 14:51:47',
   'calledstime': '2020-04-28 14:51:43',
   'calledetime': '2020-04-28 14:51:47',
   'tapesurl': 'http://101.200.159.167:16214/dualcall_yx1_fs2_1/810003/2020-04-28/20200428145126_xxx.mp3',
   'duration': 10,
   'oriamount': 0.31,
   'customParm': 'order-id-123456'}]}
    """

    def __init__(self, pdate, ptime):
        params = dict(
            pdate=pdate,  # 为索要获取话单所在的日期（年月日）
            ptime=ptime,  # 为索要获取话单所在的时（24时刻制）
            appid=const.YTX_APPID,
            action='getCdrByTime',  # 某小时话单
            fid='4',  # 语音类接口功能编号：双向呼叫（fid="4"）
        )
        YTXReqAction.__init__(self, **params)

    def resp_check(self, resp_dic: dict):
        return resp_dic
