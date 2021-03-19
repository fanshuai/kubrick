import os
import random
import base64
from io import BytesIO
from math import ceil
from PIL import (
    Image, ImageFont, ImageDraw
)
from django.http import HttpResponse


current_path = os.path.normpath(os.path.dirname(__file__))
words_lines = open(os.path.join(current_path, 'words.list'), 'r').readlines()
words_list = [line.replace('\n', '') for line in words_lines]
words_list = [word for word in words_list if word]


class DjangoVerifyCode(object):
    session_name = 'django-verify-code'

    def __init__(self, request):
        self.django_request = request
        self.code, self.font_size = '', ''
        self.words = words_list

        # 验证码图片尺寸
        self.img_width = 150
        self.img_height = 50

        # 验证码字体颜色
        self.font_color = [
            'lightgrey', 'lightsalmon', 'lightgreen', 'lightblue', 'lightcoral',
            'lightsteelblue', 'lightskyblue', 'lightpink'
        ]
        # 随即背景颜色
        self.background = (250, 250, 250)
        # 字体文件路径
        self.font_path = os.path.join(current_path, 'Menlo.ttc')
        # self.font_path = os.path.join(current_path, 'timesbi.ttf')

    def _get_font_size(self):
        """
        将图片高度的80%作为字体大小
        """
        s1 = int(self.img_height * 0.8)
        s2 = int(self.img_width / len(self.code))
        return int(min((s1, s2)) + max((s1, s2)) * 0.08)

    @staticmethod
    def _get_words():
        """
        读取默认的单词表
        """
        file_path = os.path.join(current_path, 'words.list')
        f = open(file_path, 'r')
        return [row.replace('\n', '') for row in f.readlines()]

    def _set_answer(self, answer):
        """ 设置答案"""
        self.django_request.session[self.session_name] = str(answer)

    def _yield_world(self):
        """英文单词验证码"""
        code = random.sample(self.words, 1)[0]
        self._set_answer(code)
        return code

    def _yield_number(self):
        """数字公式验证码"""
        m, n = 5, 20
        x = random.randrange(m, n)
        y = random.randrange(m, n)
        r = random.randrange(0, 3)
        if x < 10 and y < 10:
            code = "%s * %s = ?" % (x, y)
            z = x * y
        elif r > 0 and x > y:
            code = "%s - %s = ?" % (x, y)
            z = x - y
        else:
            code = "%s + %s = ?" % (x, y)
            z = x + y
        self._set_answer(z)
        return code

    def _yield_code(self):
        """生成验证码文字,以及答案"""
        return random.randint(0, 1) and self._yield_world() or self._yield_number()

    def display(self, b64encode=False):
        """
        验证码生成
        :param b64encode:  是否以base64编码
        :return: HttpResponse or tuple
        """
        im = Image.new('RGB', (self.img_width, self.img_height), self.background)
        self.code = self._yield_code()

        # 更具图片大小自动调整字体大小
        self.font_size = self._get_font_size()

        # creat a pen
        draw = ImageDraw.Draw(im)

        # 画随机干扰线,字数越少,干扰线越多
        for i in range(random.randrange(5, 6)):
            line_color = (
                random.randrange(160, 255),
                random.randrange(160, 255),
                random.randrange(160, 255),
            )
            xy = (
                random.randrange(0, self.img_width),
                random.randrange(0, self.img_height),
                random.randrange(0, self.img_width),
                random.randrange(0, self.img_height),
            )
            draw.line(xy=xy, fill=line_color, width=2)
            start, end = random.randrange(0, 360), random.randrange(0, 360)
            draw.arc(xy=xy, start=start, end=end, fill=line_color)

        # 写验证码  # 起始位置
        x = random.randrange(int(self.font_size * 0.4), int(self.font_size * 0.6))
        for i in self.code:
            # 上下抖动量,字数越多,上下抖动越大
            y = random.randrange(int(0.8 * len(self.code)), int(2 * len(self.code)))
            if i in ('+', '=', '?') or i.isdigit():
                # 对计算符号等特殊字符放大处理
                m = ceil(self.font_size * 0.6)
            else:
                # 字体大小变化量,字数越少,字体大小变化越多
                m = random.randrange(0, int(80 / self.font_size + self.font_size / 8))

            code_font = ImageFont.truetype(
                self.font_path,
                self.font_size + int(ceil(m)),
            )
            draw.text((x, y), i, font=code_font, fill=random.choice(self.font_color))
            x += self.font_size * 0.8

        del x
        del draw
        buf = BytesIO()
        im.save(buf, 'gif')
        assert not buf.closed
        content_type = 'image/gif'
        if b64encode:
            detail = base64.b64encode(buf.getvalue()).decode('utf-8')
            return f'data:{content_type};base64, {detail}'
        return HttpResponse(content=buf.getvalue(), content_type=content_type)

    def check(self, code):
        """
        检查用户输入的验证码是否正确
        """
        _code = self.django_request.session.get(self.session_name) or ''
        if not _code:
            return False
        return _code.lower() == str(code).lower()

    def value(self):
        """
        获取当前验证码内容
        """
        return self.django_request.session.get(self.session_name) or ''


if __name__ == '__main__':
    pass
    # import mock
    # request = mock.Mock()
    # c = Code(request)
