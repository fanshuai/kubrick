"""
django/contrib/auth/validators.py
"""
import re

from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

from server.constant import blocks

# 三个相同字符
same_pattern = re.compile(r'(\w)\1{2,}')


@deconstructible
class UsercodeValidator(validators.RegexValidator):
    """ 用户码 """
    regex = r'^[a-z]{7}$'
    message = '只能为7位字母'
    flags = re.ASCII

    def __call__(self, value):
        # if same_pattern.search(value):
        #     raise ValidationError('相同字母过多')
        if str(value).lower() in blocks.block_usercodes:
            raise ValidationError('已被禁用')
        for key in blocks.block_usercode_keys:
            if key in str(value).lower():
                raise ValidationError('包含关键词')
        super().__call__(value)


usercode_validator = UsercodeValidator()


@deconstructible
class SymbolValidator(validators.RegexValidator):
    """ 场景码 """
    regex = r'^[a-z]{10}$'
    message = '只能为10位纯字母'
    flags = re.ASCII


symbol_validator = SymbolValidator()
