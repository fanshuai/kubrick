import json
import logging
from enum import unique
from django.db.models import IntegerChoices
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger('kubrick.debug')


@unique
class APICodes(IntegerChoices):
    """ 自定义业务状态码，HTTP状态码2**时使用 """
    ok = 0, '成功',
    fail = -1,  '失败'
    # ##########
    limit = -100, '业务限制'
    # ##########
    third = -300, '上游业务异常'
    # ##########
    error = -500, '系统异常'


class APIResponse(object):
    """ 标准API返回 """

    def __init__(self, _cd=APICodes.ok.value, _msg=APICodes.ok.label, data=None):
        assert isinstance(data, dict), type(data).__name__
        self._cd, self._msg = _cd, _msg
        self.data = data

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        assert isinstance(self.data, dict)
        self.data.update(_cd=self._cd, _msg=self._msg)
        return self.data

    def to_json(self):
        content = json.dumps(self.to_dict(), ensure_ascii=False, cls=DjangoJSONEncoder)
        return content


class APIOKResp(APIResponse):
    """ 成功API返回 """
    def __init__(self, _msg=APICodes.ok.label, data=None):
        super().__init__(_cd=APICodes.ok.value, _msg=_msg, data=data)


class APIFailResp(APIResponse):
    """ 失败API返回 """
    def __init__(self, _msg=APICodes.fail.label, data=None):
        super().__init__(_cd=APICodes.fail.value, _msg=_msg, data=data)
