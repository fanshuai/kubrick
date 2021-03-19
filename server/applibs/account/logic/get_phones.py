from server.applibs.account.models import Phone
from server.applibs.account.schema.serializer import PhoneSerializer


def get_user_phones(usrid):
    """ 获取用户手机号信息 """
    phone_qs = Phone.objects.user_phone_qs(usrid)
    phone_main = Phone.objects.user_phone_main(usrid)
    main = PhoneSerializer(phone_main).data
    phones = PhoneSerializer(phone_qs, many=True).data
    data = dict(main=main, phones=phones, limit=Phone.limit)
    return data
