"""
触发会话
"""
import logging
from server.constant import mochoice as mc

logger = logging.getLogger('kubrick.debug')


def trigger_conv_by_ocr(usrid, result, vehicle, location=None):
    """ 触发会话，车牌号识别 """
    trigger = result['trigger']
    assert trigger == mc.TriggerType.OCR, trigger
    from server.applibs.release.models import Vehicle, Symbol
    from server.applibs.convert.models import Contact, Message
    if not isinstance(vehicle, Vehicle):
        return False, '尚未注册绑定'
    if not vehicle.usrid:
        return False, '车牌尚未绑定'
    elif vehicle.usrid == usrid:
        return False, '您自己的车牌'
    symbol = Symbol.objects.get(symbol=vehicle.symbol, usrid=vehicle.usrid)
    assert symbol.usrid == vehicle.usrid, f'{symbol.symbol} {vehicle.pk}'
    if not symbol.is_usable:
        return False, '车牌信息无效'
    elif symbol.is_closed:
        return False, '暂无法联系'
    elif not symbol.is_user_active:
        return False, '暂时无法联系'
    contact = Contact.objects.link_contact(
        usrid, symbol.usrid,
        symbol=symbol.symbol,
    )
    content = f'通过车牌号识别查找'
    key = symbol.symbol
    Message.objects.trigger_msg_add(
        contact, trigger, content,
        key, location=location
    )
    contact.add_keyword(symbol.symbol)
    contact.add_keyword(symbol.title)
    Symbol.objects.count_trigger_update(symbol)
    return True, contact


def trigger_conv_by_symbol(usrid, result, location=None):
    """ 触发会话，扫场景码 """
    trigger = result['trigger']
    assert trigger == mc.TriggerType.Symbol, trigger
    from server.applibs.release.models import Symbol
    from server.applibs.convert.models import Contact, Message
    try:
        key = result['key']
        hotp = result['hotp']
        symbol = Symbol.objects.get(symbol=key)
    except (KeyError, Symbol.DoesNotExist):
        return False, '场景码不存在'
    if not symbol.is_usable:
        return False, '场景码无效'
    elif not symbol.hotp_at == hotp:
        return False, '场景码已失效'
    elif symbol.usrid == usrid:
        return False, f'自己的{symbol.scened}'
    elif symbol.is_closed:
        return False, '暂无法联系'
    elif not symbol.is_user_active:
        return False, '暂时无法联系'
    content = f'通过{symbol.scened}[{symbol.tail}]查找'
    contact = Contact.objects.link_contact(usrid, symbol.usrid, symbol=key)
    Message.objects.trigger_msg_add(
        contact, trigger, content,
        key, location=location
    )
    contact.add_keyword(symbol.symbol)
    contact.add_keyword(symbol.title)
    Symbol.objects.count_trigger_update(symbol)
    return True, contact


def trigger_conv_by_usercode(usrid, result, location=None):
    """ 触发会话，扫用户码 """
    trigger = result['trigger']
    assert trigger == mc.TriggerType.UserCode, trigger
    from server.applibs.account.models import AuthUser, UserCode
    from server.applibs.convert.models import Contact, Message
    try:
        key = result['key']
        hotp = result['hotp']
        usercode = UserCode.objects.get(code=key)
    except (KeyError, UserCode.DoesNotExist):
        return False, '二维码不存在'
    user = AuthUser.objects.get(pk=usercode.usrid)
    if not user.is_active:
        return False, '暂不可用'
    elif not usercode.hotp_at == hotp:
        return False, '二维码已失效'
    elif usercode.usrid == usrid:
        return False, '自己的二维码'
    content = f'通过用户码[{usercode.tail}]查找'
    contact = Contact.objects.link_contact(usrid, usercode.usrid, symbol=key)
    Message.objects.trigger_msg_add(
        contact, trigger, content,
        key, location=location
    )
    contact.add_keyword(usercode.code)
    return True, contact


def qrcode_trigger(usrid, result):
    """ 扫码触发会话 """
    from server.applibs.convert.models import Contact
    trigger = result['trigger']
    func_dic = {
        mc.TriggerType.Symbol: trigger_conv_by_symbol,
        mc.TriggerType.UserCode: trigger_conv_by_usercode,
    }
    func = func_dic.get(trigger)
    if callable(func):
        is_ok, resp = func(usrid, result)
    else:
        is_ok, resp = False, '无法识别的二维码'
    if is_ok:
        assert isinstance(resp, Contact)
    return is_ok, resp


def qrcode_bind(usrid, result):
    """ 场景码扫码绑定 """
    from server.applibs.release.models import Publication, Symbol
    usable_pub = Publication.objects.get_usable_publication(result['key'])
    if isinstance(usable_pub, Publication):
        is_ok, resp = usable_pub.activate(usrid)
    else:
        is_ok, resp = False, '二维码无效或暂不可用'
    if is_ok:
        assert isinstance(resp, Symbol)
    return is_ok, resp
