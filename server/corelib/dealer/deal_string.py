"""
字符串处理
"""
import re
import emoji

rec_emoji = emoji.get_emoji_regexp()
rec_newlines = re.compile(r'\n+')


def filter_emoji(txt, restr='*'):
    """ 过滤除Emoji字符 """
    return rec_emoji.sub(restr, txt)


def filter_newlines(txt, restr='\n'):
    """ 多个换行替换至一个 """
    return rec_newlines.sub(restr, txt)
