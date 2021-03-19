"""
二维码工具

身份证尺寸：约 856 * 540
"""
import os
import math
import qrcode
import base64
from io import BytesIO
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

from kubrick.initialize import BASE_DIR, QRIMG_LOGO, DEFAULT_AVATAR
from server.third.aliyun import bucket_internal
from server.third.aliyun.oss import image_square_resize
from server.corelib.dealer.deal_string import filter_emoji


# 中文思源黑体
font_sans = os.path.join(BASE_DIR, 'frontend/fonts/SourceHanSansSC-Regular.otf')
img_font_sans_60 = ImageFont.truetype(font_sans, 60)
img_font_sans_48 = ImageFont.truetype(font_sans, 48)
img_font_sans_36 = ImageFont.truetype(font_sans, 36)

# 英文等宽 RobotoMono
font_roboto_medium = os.path.join(BASE_DIR, 'frontend/fonts/RobotoMono-Medium.ttf')
img_font_roboto_medium_36 = ImageFont.truetype(font_roboto_medium, 36)
img_font_roboto_medium_32 = ImageFont.truetype(font_roboto_medium, 32)

font_roboto_regular = os.path.join(BASE_DIR, 'frontend/fonts/RobotoMono-Regular.ttf')
img_font_roboto_regular_36 = ImageFont.truetype(font_roboto_regular, 36)
img_font_roboto_regular_32 = ImageFont.truetype(font_roboto_regular, 32)


def oss_avatar_qrcode(avatar, size=160):
    """" OSS头像，用户码图片使用 """
    # avatar.open()
    pil_img = Image.open(avatar)
    crop_img = image_square_resize(pil_img, size)
    return crop_img


def oss_avatar_default_qrcode(size=160):
    """" 默认头像，用户码图片使用 """
    pil_img = Image.open(DEFAULT_AVATAR)
    crop_img = image_square_resize(pil_img, size)
    return crop_img


@dataclass
class ImageSize:
    """ 图片大小，5寸照片：12.7cm*8.9cm. """
    w: int = 890
    h: int = 1270

    @property
    def half_w(self):
        return int(self.w / 2)

    @property
    def half_h(self):
        return int(self.h / 2)


imgs = ImageSize()


def get_image_encode(img):
    """ 图片Base64编码 """
    assert isinstance(img, Image.Image)
    with BytesIO() as buffer:
        img.save(buffer, format='png', optimize=True, quality=95)
        content = base64.b64encode(buffer.getvalue()).decode('utf-8')
    detail = f'data:image/png;base64,{content}'
    return detail


def get_qrcode_image(content, code):
    """ 二维码图片，V9:(636, 636)，53*53 像素 """
    box_size = 12  # 二维码像素大小
    # https://www.qrcode.com/zh/about/version.html
    qr = qrcode.QRCode(
        version=9, border=0, box_size=box_size,
        error_correction=qrcode.ERROR_CORRECT_Q,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    bg_img = Image.new('RGBA', img.size, color=(255, 255, 255, 255))
    img_w, img_h = img.size
    logo = Image.open(QRIMG_LOGO, 'r')
    logo_w, logo_h = logo.size
    bg_img.paste(img, (0, 0))
    # return bg_img
    point_w = round((img_w - logo_w) / 2)
    point_h = round((img_h - logo_h) / 2)
    bg_img.paste(logo, (point_w, point_h))
    # bg_img.paste(logo, (point_w, point_h), mask=logo)
    # ############ 二维码编码
    code_w, code_h = img_font_roboto_medium_36.getsize(code)
    # 进一法，占满二维码像素
    code_bg_h = math.ceil(code_h / box_size) * box_size
    code_bg_w = math.ceil(code_w / box_size) * box_size + box_size
    # ############ 二维码编码图片生成
    code_img = Image.new('RGBA', (code_bg_w, code_bg_h), color=(255, 255, 255, 255))
    code_draw = ImageDraw.Draw(code_img)
    # code_text_h = img_h - code_bg_h + round((code_bg_h - code_h) / 2)
    code_text_w, code_text_h = round((code_bg_w - code_w) / 2), 0  # 字体位置偏下调整
    code_draw.text((code_text_w, code_text_h), code, fill=(0, 0, 0), font=img_font_roboto_medium_36)
    new_code_img = code_img.transpose(Image.ROTATE_90)  # 二维码编码图片，逆时针旋转270度
    code_img_w, code_img_h = img_w - code_bg_h, box_size * 8
    bg_img.paste(new_code_img, (code_img_w, code_img_h))
    return bg_img


def paste_qrcode_image_bottom(bg_draw, bg_img, qr_img, desc, brand):
    """ 用户码底部内容 """
    # #############
    qr_w, qr_h = qr_img.size  # 二维码尺寸
    desc_size = img_font_sans_48.getsize(desc)
    desc_top = round((imgs.h + qr_h) / 2) + desc_size[1]
    desc_coordinate = round((imgs.w - desc_size[0]) / 2), desc_top
    bg_draw.text(desc_coordinate, desc, fill=(35, 35, 35), font=img_font_sans_48)
    # #############
    brand_size = img_font_sans_36.getsize(brand)
    brand_top = round((imgs.h + qr_h) / 2) + 2 * desc_size[1] + brand_size[1]
    brand_coordinate = round((imgs.w - brand_size[0]) / 2), brand_top
    bg_draw.text(brand_coordinate, brand, fill=(15, 157, 88), font=img_font_sans_36)
    # #############  二维码图片贴在中央
    bg_img.paste(qr_img, (round((imgs.w - qr_w) / 2), round((imgs.h - qr_h) / 2)))
    return bg_img


def get_user_qrcode_image(user, content):
    """ 用户码图片 """
    from server.applibs.account.models import AuthUser
    assert isinstance(user, AuthUser)
    title = user.name or '**'
    title = filter_emoji(title)
    uc_info = user.usercode_info
    codeid = f'ID: {uc_info.fmt}'
    qr_img = get_qrcode_image(content, uc_info.fmt)
    qr_w, qr_h = qr_img.size  # 二维码尺寸
    bg_img = Image.new('RGBA', (imgs.w, imgs.h), (255, 255, 255, 255))
    border = round((imgs.w - qr_w) / 2)
    bg_draw = ImageDraw.Draw(bg_img)
    avatar_size = 160
    if user.profile.avatar:  # 可能无头像
        avatar = oss_avatar_qrcode(user.profile.avatar, size=avatar_size)
    else:
        avatar = oss_avatar_default_qrcode(size=avatar_size)
    bg_img.paste(avatar, (border, round(border * 4 / 5)))
    avt_w, avt_h = avatar_size, avatar_size
    title_left = border + avt_w + round(border / 5)
    title_coordinate = title_left, round(border * 4 / 5) + 5
    bg_draw.text(title_coordinate, title, user.profile.gender_rgb, font=img_font_sans_60)
    codeid_coordinate = title_left, round(border * 4 / 5) + round(avt_h / 2) + 15
    bg_draw.text(codeid_coordinate, codeid, fill=(35, 35, 35), font=img_font_roboto_regular_36)
    right_shape = [(imgs.w - border, border), (imgs.w, border + avt_h)]
    bg_draw.rectangle(right_shape, fill=(255, 255, 255))  # 名字溢出覆盖
    bt_desc, bt_brand = '微信扫码可与我联系', '便捷高效 安全可控'
    bg_img = paste_qrcode_image_bottom(bg_draw, bg_img, qr_img, bt_desc, bt_brand)
    return bg_img


def get_symbol_qrimg_simple(symbol):
    """ 场景码二维码图片 """
    from server.applibs.release.models import Symbol, Publication
    assert isinstance(symbol, (Symbol, Publication))
    qr_img = get_qrcode_image(symbol.qr_uri, symbol.fmt)
    return qr_img


def get_qrimg_shifting_symbol_default(oss_key, base_encode=True):
    """ 【经典白挪车码】B64编码 """
    qr_img = Image.open(BytesIO(bucket_internal.get_object(oss_key).read()))
    qr_w, qr_h = qr_img.size  # 二维码尺寸
    bg_img = Image.new('RGBA', (imgs.w, imgs.h), color=(255, 255, 255, 255))
    bg_draw = ImageDraw.Draw(bg_img)
    title = '临时停靠 请多关照'
    img_font = ImageFont.truetype(font_sans, 60)
    title_bg_h = round((imgs.h - qr_h) / 2)
    title_w, title_h = img_font.getsize(title)
    line_left = round((imgs.w - title_w) / 2)
    line_top = round((title_bg_h - title_h) / 2)
    bg_draw.text((line_left, line_top), title, fill=(0, 0, 0), font=img_font)
    bt_desc, bt_brand = '微信扫码 呼叫挪车', '便捷高效 保护隐私 安全可控'
    bg_img = paste_qrcode_image_bottom(bg_draw, bg_img, qr_img, bt_desc, bt_brand)
    if not base_encode:
        return bg_img
    detail = get_image_encode(bg_img)
    return detail
