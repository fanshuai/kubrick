"""
图片异步处理
"""
import logging
from io import BytesIO

from PIL import Image
from oss2 import OBJECT_ACL_PUBLIC_READ

from kubrick.celery import app

from server.constant.djalias import CQueueAlias
from server.third.aliyun import bucket_internal
from server.third.aliyun.oss import OSSDir, oss_has_key
from server.third.aliyun.oss.oss_actions import image_square_resize

logger = logging.getLogger('kubrick.celery')


@app.task(queue=CQueueAlias.Default.value)
def oss_avatar_compress(key):
    """" OSS头像压缩 """
    result = dict(
        task='oss_avatar_compress',
        key=key, reason='success',
    )
    size = 520  # 最大尺寸
    if OSSDir.Avatar.value not in str(key):
        result['reason'] = 'not avatar'
    if not oss_has_key(key):
        result['reason'] = 'key not exists'
    pil_img = Image.open(BytesIO(bucket_internal.get_object(key).read()))
    img_w, img_h = pil_img.size
    if max([img_w, img_h]) <= size:
        bucket_internal.put_object_acl(key, OBJECT_ACL_PUBLIC_READ)
        result['reason'] = 'compressed'
        return result
    crop_img = image_square_resize(pil_img, size)
    assert isinstance(crop_img, Image.Image)
    with BytesIO() as buffer:
        headers = {'Content-Type': 'image/jpeg', 'x-oss-object-acl': OBJECT_ACL_PUBLIC_READ}
        crop_img.save(buffer, format='jpeg', optimize=True, quality=99)
        oss_resp = bucket_internal.put_object(key, buffer.getvalue(), headers=headers)
    if not oss_resp.status == 200:
        result['reason'] = f'put fail: {oss_resp.resp}'
    return result


@app.task(queue=CQueueAlias.Default.value)
def update_usercode_qrimg(usrid):
    """ 用户二维码图片更新 """
    from server.applibs.account.models import UserCode
    try:
        uc_info = UserCode.objects.get(usrid=usrid)
        uc_info.qrimg_save()
    except UserCode.DoesNotExist:
        reason = f'not_exist {usrid}'
        logger.exception(reason)
    except Exception as exc:
        reason = f'error {str(exc)}'
        logger.exception(reason)
    else:
        reason = 'success'
    result = dict(
        task='update_usercode_qrimg',
        usrid=usrid, reason=reason,
    )
    return result
