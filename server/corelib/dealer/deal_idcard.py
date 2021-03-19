"""
身份证号校验
"""
import re


def is_valid_idcard(idcard):
    if isinstance(idcard, int):
        idcard = str(idcard)
    if not re.match('[1-9][0-9]{14}([0-9]{2}[0-9X])?', idcard):
        return False
    items = [int(item) for item in idcard[:-1]]
    ## 加权因子表
    factors = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    ## 计算17位数字各位数字与对应的加权因子的乘积
    copulas = sum([a * b for a, b in zip(factors, items)])
    ## 校验码表
    ckcodes = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')
    is_ok = ckcodes[copulas % 11].upper() == idcard[-1].upper()
    return is_ok
