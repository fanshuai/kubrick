from .access_token import *

RTCRoleAttendee = 0  # depreated, same as publisher
RTCRolePublisher = 1  # for live broadcaster
RTCRoleSubscriber = 2  # default, for live audience
RTCRoleAdmin = 101  # deprecated, same as publisher


def get_rtc_token(channel, user, role=RTCRoleAttendee):
    expired_ts = int(time.time()) + 3600
    token = AccessToken(channel, user)
    token.add_privilege(kJoinChannel, expired_ts)
    if (role == RTCRoleAttendee) | (role == RTCRoleAdmin) | (role == RTCRolePublisher):
        token.add_privilege(kPublishVideoStream, expired_ts)
        token.add_privilege(kPublishAudioStream, expired_ts)
        token.add_privilege(kPublishDataStream, expired_ts)
    key = token.build()
    logger.info(f'get_rtc_token {channel}-{user}-{role}: {key}')
    return key


def get_rtm_token(user):
    expired_ts = int(time.time()) + 3600
    token = AccessToken(user, '')
    token.add_privilege(kRtmLogin, expired_ts)
    key = token.build()
    logger.info(f'get_rtm_token {user}: {key}')
    return key
