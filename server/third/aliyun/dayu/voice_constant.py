from enum import unique
from collections import OrderedDict
from django.db.models import IntegerChoices, TextChoices


@unique
class ALICallStage(IntegerChoices):
    """ 语音双呼进度，按时间顺序 """
    CallCaller = 10, '呼叫主叫'
    CallerBell = 20, '主叫响铃'
    CallerAnswer = 30, '主叫接听'  # 开始 呼叫被叫
    CalledBell = 40, '被叫响铃'  # 添加
    CalledAnswer = 50, '被叫接听'
    CallHangUp = 60, '呼叫结束'


@unique
class ALICallStatus(TextChoices):
    """ 语音双呼状态，阿里云 """
    # https://help.aliyun.com/document_detail/112804.html
    CallCaller = '200101', '呼叫主叫'
    CallerBell = '200201', '主叫响铃'
    CallerAnswer = '200102', '主叫接听'  # 开始 呼叫被叫
    CalledBell = '200202', '被叫响铃'
    CalledAnswer = '200103', '被叫接听'
    CallHangUp = '200100', '呼叫结束'


ALI_CALL_STATE_MAP = (
    (ALICallStatus.CallCaller, ALICallStage.CallCaller),
    (ALICallStatus.CallerBell, ALICallStage.CallerBell),
    (ALICallStatus.CallerAnswer, ALICallStage.CallerAnswer),
    (ALICallStatus.CalledBell, ALICallStage.CalledBell),
    (ALICallStatus.CalledAnswer, ALICallStage.CalledAnswer),
    (ALICallStatus.CallHangUp, ALICallStage.CallHangUp),
)

ALI_CALL_STATUS_STAGE_DIC = OrderedDict(((k.value, v.value) for k, v in ALI_CALL_STATE_MAP))
ALI_CALL_STAGE_STATUS_DIC = OrderedDict(((v.value, k.value) for k, v in ALI_CALL_STATE_MAP))