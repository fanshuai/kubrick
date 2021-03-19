"""
金额处理

https://www.zhihu.com/question/20128906
Python 为什么不解决四舍五入(round)的“bug”？
"""
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP


def format_decimal(d):
    """ 保留两位小数，四舍五入 """
    d = Decimal(str(d))
    fd = d.quantize(Decimal('0.00'), ROUND_HALF_UP)
    return fd


def format_decimal__up(d):
    """ 保留两位小数，向上取整 """
    d = Decimal(str(d))
    fd = d.quantize(Decimal('0.00'), ROUND_UP)
    return fd


def format_decimal__down(d):
    """ 保留两位小数，向下取整 """
    d = Decimal(str(d))
    fd = d.quantize(Decimal('0.00'), ROUND_DOWN)
    return fd


def decimal_round(d, n=0):
    """ 小数四舍五入 """
    assert 0 <= n <= 20
    d = Decimal(str(d))
    rd_str = '0' * n  # 取几位小数
    fd = d.quantize(Decimal(f'0.{rd_str}'), ROUND_HALF_UP)
    return fd


def fen_to_yuan(d):
    """ 分转元 """
    assert isinstance(d, (int, float))
    yuan = Decimal(str(d / 100))
    fd = yuan.quantize(Decimal('0.00'), ROUND_HALF_UP)
    return fd


def fen_to_yuan_str(d):
    """ 分转元，字符串 """
    fd = fen_to_yuan(d)
    fd_str = str(fd)
    return fd_str
