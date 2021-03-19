from server.constant.mochoice import PNVScene, SMSNoticeScene

# 短信签名
SMS_SIGN = '道我'

# 短信模板模板，依赖参数：code、name、tail、other
ALL_SMS_TEMPLATES = {
    # 验证码
    'SMS_175543533': '{code} 是您的验证码，五分钟内有效。',
    'SMS_189621101': '{code} 是您的验证码，五分钟内有效。你正在进行登录或注册操作。',  # 登录或注册
    'SMS_189521735': '{code} 是您的验证码，五分钟内有效。你正在进行绑定手机号操作。',  # 绑定手机号
    'SMS_189616383': '{code} 是您的验证码，五分钟内有效。你正在进行解绑手机号操作。',  # 解绑手机号
    'SMS_189611296': '{code} 是您的验证码，五分钟内有效。你正在进行场景码删除操作。',  # 场景码删除
    # 短信提醒：短信通知类型
    'SMS_205398322': '消息未读提醒：{name}给你发送了消息，请登录微信[道我]小程序查看或回复。',
    'SMS_205393460': '来电未接提醒：{name}尝试与你通话但未能接通，请登录微信[道我]小程序查看或回拨。',
    'SMS_205445081': '消息提醒：{name}在{diff}给你发送了消息，请登录微信[道我]小程序查看或回复。',
    'SMS_205440169': '来电提醒：{name}在{diff}尝试与你通话但未能接通，请登录微信[道我]小程序查看或回拨。',
}

# 验证码 (0.045元/条)
SMS_CODE_SCENE_MAP = {
    PNVScene.Sign: 'SMS_189521735',
    PNVScene.Bind: 'SMS_189521735',
    PNVScene.Unbind: 'SMS_189616383',
    PNVScene.UNSymbol: 'SMS_189611296',
}
# 短信通知 (0.045元/条)
SMS_NOTICE_SCENE_MAP = {
    SMSNoticeScene.MSGUnread: 'SMS_205445081',
    SMSNoticeScene.MSGMissed: 'SMS_205440169',
}


def sms_mock_content(code, params):
    """ 模拟短信内容 """
    template = ALL_SMS_TEMPLATES[code]
    content = template.format(**params)
    content = f'【{SMS_SIGN}】{content}'
    return content
