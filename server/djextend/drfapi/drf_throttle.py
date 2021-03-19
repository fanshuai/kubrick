"""
from rest_framework.throttling import ScopedRateThrottle
http://www.django-rest-framework.org/api-guide/throttling/

The rate descriptions used in DEFAULT_THROTTLE_RATES may include:
second, minute, hour or day as the throttle period.

http://www.django-rest-framework.org/api-guide/throttling/
"""
from enum import Enum
from collections import OrderedDict


class ScopedThrottles(Enum):
    # AnonRateThrottle
    Anon = '100/minute'
    # UserRateThrottle
    User = '200/minute'

    # ScopedRateThrottle
    LogIn = '20/minute'
    SignIn = '20/minute'
    LogOut = '30/minute'
    Profile = '60/minute'
    Passowrd = '10/hour'
    Remind = '3/minute'
    Call = '50/day'  # TODO


THROTTLE_RATES_DICT = OrderedDict(
    (k.lower(), v.value) for k, v in ScopedThrottles.__members__.items()
)

if __name__ == '__main__':
    print(THROTTLE_RATES_DICT)
