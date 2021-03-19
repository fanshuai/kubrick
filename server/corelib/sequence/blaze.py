"""
用户码生成:
    简短好看、规则统一、易于记忆和传播
    7位纯字母 容量：26**7(八十亿)

场景码生成:
    10位纯数字
    容量：26**10

其他:
    ASCII: A ~ Z > 65 ~ 90
    字体：等宽！
"""
import random


letter_seeds = ''.join(chr(i + 65) for i in range(26))


def random_seq(pkid: int, length: int) -> str:
    """
    26字母随机码生成
    """
    mod = pkid % 26
    part_a = chr(mod + 65)
    part_random = ''.join(random.sample(letter_seeds, length))
    code = str(part_a + part_random).lower()
    return code


def user_code_seq(pkid: int) -> str:
    """
    用户码随机生成，7位纯字母
    """
    code = random_seq(pkid, 6)
    return code


def symbol_code_seq(pkid: int) -> str:
    """
    场景码随机生成，10位纯字母
    """
    code = random_seq(pkid, 9)
    return code


if __name__ == '__main__':
    for i in range(9):
        rid = random.randint(int(1e5) + i, int(1e6) - 1)
        s_code = symbol_code_seq(rid)
        u_code = user_code_seq(rid)
        print(f'{rid}: {s_code} {u_code}')
    rid = random.randint(int(1e5), int(1e6) - 1)
    s_code = symbol_code_seq(rid)
    u_code = user_code_seq(rid)
    print(f'{rid}: {s_code} {u_code}')
