"""
阿里云图片上传
    1. 客户端直接上传OSS，服务端签名 https://help.aliyun.com/document_detail/31926.html
"""
import hmac
import json
import base64
import logging
import pendulum
from PIL import Image
from io import BytesIO
from hashlib import sha1 as sha
from django.core.files.uploadedfile import UploadedFile

from server.corelib.sequence import idshift
from server.corelib.dealer.deal_time import get_now
from server.third.aliyun import bucket_public, bucket_internal
from server.third.aliyun.oss.oss_path import get_oss_key, OSSDir
from server.third.aliyun import ak_cfg, bucket_cfg

logger = logging.getLogger('kubrick.debug')


def fe_oss_token(scene, ext, usrid):
    """ 客户端直接上传OSS，服务端签名 """
    assert isinstance(usrid, int) and usrid > 0, usrid
    name = f'{idshift.generate_captcha()}.{ext}'
    oss_key = get_oss_key(scene, name, usrid)
    expire_syncpoint = int(get_now().add(seconds=30).timestamp())
    expire_str = pendulum.from_timestamp(expire_syncpoint).to_iso8601_string()
    condition_array = [{'key': oss_key.key}]
    policy_dict = {'expiration': expire_str, 'conditions': condition_array}
    policy = json.dumps(policy_dict).strip()
    policy_encode = base64.b64encode(policy.encode())
    hsha = hmac.new(ak_cfg.secret.encode(), policy_encode, sha)
    sign_result = base64.encodebytes(hsha.digest()).strip()
    result = {
        'akid': ak_cfg.ak,
        'key': oss_key.key,
        'name': oss_key.name,
        'updir': oss_key.updir,
        'url': oss_sign_url(oss_key.key),
        'policy': policy_encode.decode(),
        'signature': sign_result.decode(),
        'host': bucket_cfg.bucket_public_url,
        'expire': expire_syncpoint,
    }
    return result


def be_image_upload(img, usrid):
    """ 服务端图片压缩上传 """
    max_size = 1500  # 最大尺寸
    assert isinstance(img, UploadedFile), type(img)
    assert isinstance(usrid, int) and usrid > 0, usrid
    name = f'{idshift.generate_captcha()}.jpeg'
    oss_key = get_oss_key(OSSDir.TmpBe, name, usrid)
    pil_img = Image.open(img.file)
    # img_hash = hash_md5(pil_img.tobytes())
    img_w, img_h = pil_img.size
    if max([img_w, img_h]) > max_size:
        scale = max_size / max([img_w, img_h])
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        new_size = new_w, new_h
        pil_img = pil_img.resize(new_size, Image.ANTIALIAS)
    assert isinstance(pil_img, Image.Image)
    pil_img = pil_img.convert('RGB')
    with BytesIO() as buffer:
        headers = {'Content-Type': 'image/jpeg'}
        pil_img.save(buffer, format='jpeg', optimize=True, quality=85)
        oss_resp = bucket_internal.put_object(oss_key.key, buffer.getvalue(), headers=headers)
    url = oss_sign_url(oss_key.key, expires=60, watermark=True)
    result = {
        'url': url,
        'key': oss_key.key,
        'name': oss_key.name,
        'updir': oss_key.updir,
        'oss_resp': {
            'status': oss_resp.status,
            'request_id': oss_resp.request_id
        },
    }
    return result


def oss_sign_url(key, expires=5 * 60, watermark=False):
    """
    获取签名URL
    :param key:  OSS key
    :param expires: 过期时间
    :param watermark:  是否带水印
    :return:
    """
    params = {}
    if watermark:
        txt_bytes = f'ifand.com'.encode()
        txt_base64 = base64.urlsafe_b64encode(txt_bytes).decode()
        process = f'image/watermark,size_20,color_222222,text_{txt_base64}'
        params.update({'x-oss-process': process})
    url = bucket_public.sign_url('GET', key, expires, params=params, slash_safe=True)
    return url


def image_square_resize(img, size):
    """ 图片正方形剪切 """
    assert isinstance(img, Image.Image)
    img_w, img_h = img.size
    sq_size = min([img_w, img_h])
    offset = round(abs(img_w - img_h) / 2)
    cut_x, cut_y = (0, offset) if img_w < img_h else (offset, 0)
    crop_img = img.crop((cut_x, cut_y, cut_x + sq_size, cut_y + sq_size))
    crop_img = crop_img.resize((size, size), Image.ANTIALIAS)
    return crop_img


def oss_image_hold_on(key: str, hold_dir: str, new_dir: str):
    """" 图片重命名，验证通过后 """
    if key.startswith(new_dir):
        return True, key
    if not key.startswith(hold_dir):
        return False, '图片路径异常'
    assert oss_has_key(key), key
    new_key = key.replace(hold_dir, new_dir)
    resp_copy = bucket_internal.copy_object(bucket_internal.bucket_name, key, new_key)
    is_copied = resp_copy.status == 200
    if not is_copied:
        return False, '图片复制失败'
    resp_del = bucket_internal.delete_object(key)
    logger.info(f'oss_image_hold_on__done {hold_dir} > {new_dir} = {key} > {new_key} : {resp_del.status}')
    return True, new_key


def oss_idcard_hold_on(key: str):
    """" 身份证图片重命名，验证通过后 """
    new_dir = str(OSSDir.IDCard)
    hold_dir = str(OSSDir.IDCardHold)
    result = oss_image_hold_on(key, hold_dir, new_dir)
    return result


def oss_has_key(key):
    """" OSS是否存在Key """
    is_exists = bucket_internal.object_exists(key)
    return is_exists
