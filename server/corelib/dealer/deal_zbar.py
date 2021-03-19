"""
二维码处理
"""
import requests
import zbarlight
from PIL import Image
from io import BytesIO


def zbar_scan_by_up(img):
    """ 通过用户上传获取二维码内容 """
    pil_img = Image.open(img.file).convert('RGB')
    codes = zbarlight.scan_codes(['qrcode'], pil_img)
    return codes


def zbar_scan_by_url(url):
    """ 通过图片地址获取二维码内容 """
    response = requests.get(url)
    pil_img = Image.open(BytesIO(response.content)).convert('RGB')
    codes = zbarlight.scan_codes(['qrcode'], pil_img)
    if isinstance(codes, list) and (len(codes) > 0):
        codes = [c.decode() for c in codes if isinstance(c, bytes)]
    else:
        codes = []
    del pil_img
    return codes
