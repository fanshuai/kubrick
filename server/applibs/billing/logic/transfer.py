"""
充值或消费

短信提醒（仅成功）：0.1元/条
手机通话（仅发起方）：0.2元/分钟

https://www.yuque.com/ifand/product/price
"""
import logging

logger = logging.getLogger('kubrick.debug')


def bill_expend_add(usrid, amount, instid, summary='消费'):
    """ 消费记录添加 """
    from server.applibs.billing.models import BillDetail
    assert (amount < 0) and (instid > 0), f'{amount} {instid}'
    inst = BillDetail.objects.filter(
        usrid=usrid, is_del=False,
        instid=instid,
    ).order_by('-pk').first()
    if isinstance(inst, BillDetail):
        logger.warning(f'bill_expend_add__ignore {inst.pk}')
        return False, f'记录[{inst.pk}]已存在'
    inst, is_created = BillDetail.objects.get_or_create(
        usrid=usrid, instid=instid,
        amount=amount, summary=summary,
    )
    logger.info(f'bill_expend_add__done {usrid} {inst.pk} {is_created}')
    inst.checkout()
    return True, inst
