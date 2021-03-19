"""
Model choices
"""
from enum import unique
from collections import OrderedDict
from django.db.models import IntegerChoices, TextChoices


@unique
class UserGender(IntegerChoices):
    """ 用户性别，同微信 """
    Male = 1, '男'
    Female = 2, '女'
    Unknown = 0, 'X'


@unique
class PNVScene(IntegerChoices):
    """ 手机号验证场景 """
    Sign = 1, '登录或注册'
    Bind = 2, '绑定手机号'
    Unbind = 4, '解绑手机号'
    UNSymbol = 10, '场景码删除'


@unique
class ScanMode(IntegerChoices):
    """ 图片扫描模式 """
    Init = 0, '初始化'
    ByQRCode = 5, '二维码'
    ByOCRVehicle = 8, 'OCR车牌号'
    Unrecognized = 999, '无法识别'


@unique
class SymbolScene(IntegerChoices):
    """ 场景码应用场景 """
    Undefined = 0, '场景码'  # 未定义
    Vehicle = 11, '挪车码'
    Baggage = 22, '行李贴'
    Petplate = 33, '宠物牌'


@unique
class SymbolStatus(IntegerChoices):
    """ 场景码状态 """
    Init = 0, '初始化'
    Bound = 20, '已绑定'  # 使用中
    Closed = 24, '已关闭'  # 用户关闭
    Deleted = 40, '已删除'  # 用户删除
    Invalid = 44, '已作废'  # 系统删除


@unique
class PublishStatus(IntegerChoices):
    """ 主题发行状态 """
    Init = 0, '初始化'
    Prepared = 10, '已就绪'
    Published = 30, '已发行'
    Activated = 50, '已激活'


@unique
class OCRType(IntegerChoices):
    """ OCR识别类型 """
    QRCode = 2, '二维码'
    VehicleNum = 5, '车牌'
    IDCardFront = 11, '身份证正面'
    IDCardBack = 12, '身份证反面'
    VehicleLicenseFront = 33, '行驶证'  # 正面


@unique
class VehicleRelation(IntegerChoices):
    """ 所有者关系 """
    Other = 0, '其他'
    Myself = 10, '自己'
    Family = 20, '家属'
    Friend = 30, '亲友'
    Worker = 40, '同事'


@unique
class VehicleType(IntegerChoices):
    """ 车牌类型 """
    Small = 11, '小型汽车'
    Energy = 22, '新能源车'
    Large = 32, '大型汽车'
    Trailer = 35, '挂车'
    Coach = 50, '教练车'
    Police = 62, '警车'
    Military = 65, '军车'
    Embassy = 72, '使领馆车'
    HKMacao = 75, '港澳车'


VEHICLE_TYPE_DIC = OrderedDict(VehicleType.choices)
TYPE_VEHICLE_DIC = OrderedDict({v: k for k, v in VehicleType.choices})
VehicleTypeSupport = [VehicleType.Small, VehicleType.Energy]  # 目前支持的车牌类型


@unique
class Suggestion(TextChoices):
    """ 建议操作 """
    Pass = 'pass', '正常'  # OCR: 未识别出目标对象
    Review = 'review', '不确定'  # OCR: 识别出目标对象
    Block = 'block', '违规'


@unique
class WXAPPType(TextChoices):
    """ 微信开放平台，应用类型 """
    MPA = 'mpa', '小程序'


@unique
class ThirdProvider(TextChoices):
    """ 第三方云服务提供商 """
    Aliyun = 'aliyun', '阿里云'
    Wechat = 'wechat', '微信'
    YTX = 'ytx', '云迅(讯众)'


@unique
class ThirdAction(TextChoices):
    """ 第三方云服务方法 """
    # 阿里云
    ALISendSms = 'SendSms', '阿里云-短信服务-发送短信'  # 短信服务
    ALIQuerySendDetails = 'QuerySendDetails', '阿里云-短信服务-查询结果'  # 短信服务
    ALISingleSendMail = 'SingleSendMail', '阿里云-邮件推送-单一发信接口'  # 邮件推送
    ALIImageSyncScan = 'ImageSyncScan', '阿里云-内容安全-图片OCR识别'  # 内容安全
    ALITextScan = 'TextScan', '阿里云-内容安全-文本反垃圾'  # 内容安全
    # 微信(小程序)
    WXAccessToken = 'auth.getAccessToken', '微信-小程序-接口调用凭据'
    WXCodeSession = 'auth.code2Session', '微信-小程序-登录凭证校验'
    WXPaidUnionId = 'auth.getPaidUnionId', '微信-小程序-获取支付UnionId'
    WXMsgSecCheck = 'security.msgSecCheck', '微信-小程序-内容安全文本违规'
    WXSubscribeSend = 'subscribeMessage.send', '微信-小程序-发送订阅消息'
    # 云迅/讯众（双呼通话）
    YTXCallDailBack = 'xunzhong.dailBackCall', '云讯-双向呼叫'
    YTXQueryBlance = 'xunzhong.queryBlance', '云讯-查询余额'
    YTXCallCdr = 'xunzhong.callCdr', '云讯-话单获取'


@unique
class ThirdResultType(TextChoices):
    """ 第三方调用结果类型 """
    ReqExc = 'exc', '请求异常'
    RespExc = 'error', '返回异常'
    RespFail = 'failure', '返回失败'
    Success = 'success', '调用成功'


@unique
class TriggerType(IntegerChoices):
    """ 触发会话类型 """
    # 会话触发消息
    OCR = 11, '车牌号识别'
    Symbol = 15, '扫场景码'
    UserCode = 16, '扫用户码'


@unique
class MSGType(IntegerChoices):
    """ 会话消息类型 """
    Trigger = 1, '触发消息'
    StayMsg = 2, '留言消息'
    CallMsg = 5, '双呼通话'


@unique
class LCEvent(IntegerChoices):
    """ RTM 事件同步客户端 """
    OpenConv = 10, '打开会话'  # 未读更新
    NewMessage = 20, '新消息'
    ReachCall = 52, '通话触达状态'  # 文本消息，触达状态更新
    BillPush = 88, '账单推送'  # 文本消息，账单推送


@unique
class SMSNoticeScene(TextChoices):
    """ 短信提醒应用场景 """
    MSGUnread = 'msg-unread', '消息未读提醒'
    MSGMissed = 'msg-missed', '来电未接提醒'


SMS_NOTICE_SCENE_DIC = OrderedDict(SMSNoticeScene.choices)


@unique
class SMSStatus(IntegerChoices):
    """ 短信发送状态，阿里云 """
    Init = 0, '待发送'
    Waiting = 1, '等待回执'
    Failure = 2, '发送失败'
    Success = 3, '发送成功'


SMS_STATUS_DIC = OrderedDict(SMSStatus.choices)


@unique
class CallStatus(IntegerChoices):
    """ 语音双呼状态，给用户的提示内容 """
    NOTCall = 0, '-'  # 非通话记录
    OUTCaller = 210, '正在呼叫'  # 进行中: 正在呼叫主叫及响铃
    OUTCalled = 220, '正在转接'  # 进行中: 正在呼叫被叫及响铃
    ONCalling = 300, '正在通话'  # 进行中: 主被叫均接通
    ENDCaller = 410, '呼叫取消'  # 未接通: 主叫挂断或未应答
    ENDCalled = 420, '暂未接通'  # 未接通: 被叫挂断或未应答
    ENDOKCall = 500, '通话结束'  # 正常: 通话结束


CALL_STATUS_DIC = OrderedDict(CallStatus.choices)


@unique
class ReportKind(IntegerChoices):
    """ 用户举报类型 """
    # 第一版，1打头
    Other = 0, '其他'
    LJXY = 120, '垃圾营销'
    EYSR = 130, '恶意骚扰'
    SQDS = 140, '色情低俗'
    QZWX = 150, '欺诈威胁'
    YHWF = 160, '有害违法'


REPORT_KIND_DIC = OrderedDict(ReportKind.choices)


@unique
class PayType(IntegerChoices):
    """ 支付类型 """
    Charge = 1, '充值'
    Prints = 2, '打印'
    PayCall = 10, '通话账单'


@unique
class PayStatus(IntegerChoices):
    """ 支付状态 """
    Off = 0, '已关闭'
    Init = 10, '待支付'
    Done = 20, '成功'
    Fail = 40, '失败'


@unique
class PTOItemType(IntegerChoices):
    """ 打印订单明细类型 """
    ESFee = 0, '快递费'
    QRUser = 10, '用户码'
    QRScene = 20, '场景码'


WXSMTID_MAP = OrderedDict((
    (MSGType.StayMsg, 'DVOmo8aixP5Zu7Y6SewZ4qnhbVENGJgdoIqqqJgcxMc'),  # 消息未读提醒
    (MSGType.CallMsg, 'ihGOZxgR-80yerah7ZUH9K9-z08gY_WFErniZKd9c3k'),  # 来电未接提醒
))

WXSMTID_CATE = {v: k for k, v in WXSMTID_MAP.items()}


@unique
class ConfCate(TextChoices):
    """ 系统配置类型 """

    UCOff = 'uc-off', '用户码及通话关闭'
