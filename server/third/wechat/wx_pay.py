"""
微信支付
"""
from wechatpy.pay import WeChatPay

from kubrick.initialize import IS_PROD_ENV, RUN_ENV

# 微信小程序ID
WXMPA_APPID = 'wx89c0f571e16ddf81'

# 微信支付商户号
WXPAY_MCHID = '1587611791'
# 微信商户平台(pay.weixin.qq.com)->账户设置->API安全->密钥设置
WXPAY_KEY = '0ecacea6736452db95ea36a4245129dd'

# 支付结果 通知
if IS_PROD_ENV:
    CBAPI_NOTIFY = 'https://api.ifand.com/cb/wxpay'
else:
    CBAPI_NOTIFY = 'http://xhie2s.natappfree.cc/cb/wxpay'

# 支付回调返回内容
CB_RES = b"""<xml>
  <return_code><![CDATA[SUCCESS]]></return_code>
  <return_msg><![CDATA[OK]]></return_msg>
</xml>"""


# 微信支付接口
WECHAT_PAY = WeChatPay(
    appid=WXMPA_APPID,
    api_key=WXPAY_KEY,
    mch_id=WXPAY_MCHID,
)


def create_unifiedorder(openid, amount, trade_no, body='支付'):
    """ 统一下单接口 """
    body = body if IS_PROD_ENV else f'【测试-{RUN_ENV}】{body}'
    resp_dic = WECHAT_PAY.order.create(
        'JSAPI', body, amount, CBAPI_NOTIFY,
        user_id=openid, out_trade_no=trade_no,
    )
    return resp_dic


def get_jsapi_params(prepay_id):
    """ 公众号网页JS支付接口 """
    params = WECHAT_PAY.jsapi.get_jsapi_params(prepay_id)
    return params


def get_orderquery(trade_no):
    """ 查询订单 """
    # SUCCESS—支付成功
    # REFUND—转入退款
    # NOTPAY—未支付
    # CLOSED—已关闭
    # REVOKED—已撤销（刷卡支付）
    # USERPAYING--用户支付中
    # PAYERROR--支付失败(其他原因，如银行返回失败)
    resp_dic = WECHAT_PAY.order.query(out_trade_no=trade_no)
    assert WECHAT_PAY.check_signature(resp_dic), f'fail: {resp_dic}'
    return resp_dic


# 明确失败的状态
FAIL_STATES = ['CLOSED', 'REVOKED', 'PAYERROR']  # NOTPAY
