import logging
import phonenumbers

from server.constant import normal

logger = logging.getLogger('kubrick.debug')


def parse_phonenumber(number):
    """ 解析电话号码及检查是否有效 """
    if isinstance(number, str):
        pass
    elif isinstance(number, bytes):
        number = number.decode()
    else:
        number = str(number)
    numobj = phonenumbers.parse(number, region=normal.RGCN)
    assert phonenumbers.is_valid_number(numobj), 'is_valid_number'
    assert phonenumbers.is_possible_number(numobj), 'is_possible_number'
    assert numobj.country_code in normal.COUNTRY_CODES, f'country_not_support'
    return numobj


def format_phonenumber(numstr):
    """ 获取 E.164 Number """
    try:
        numobj = parse_phonenumber(numstr)
    except phonenumbers.NumberParseException as exc:
        number, message = None, f'parse_error {str(exc)}'
    except AssertionError as exc:
        number, message = None, f'not_valid {str(exc)}'
    else:
        number = phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
        message = phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return number, message
    logger.warning(f'format_phonenumber__aborted {numstr}: {message}')
    return number, message


def format_phonenumber_national(numstr):
    """ 获取 National Number """
    try:
        numobj = parse_phonenumber(numstr)
    except phonenumbers.NumberParseException as exc:
        number, message = None, f'parse_error {str(exc)}'
    except AssertionError as exc:
        number, message = None, f'not_valid {str(exc)}'
    else:
        number = str(numobj.national_number)
        message = phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return number, message
    logger.warning(f'format_phonenumber_national__aborted {numstr}: {message}')
    return number, message
