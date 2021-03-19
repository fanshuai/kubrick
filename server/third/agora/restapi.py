import json
import logging
from django.core.serializers.json import DjangoJSONEncoder

from kubrick.initialize import AGORA_APPID
from server.third.agora.access import get_rtm_token
from server.corelib.utils.req_retry import get_retry_session


logger = logging.getLogger('kubrick.debug')

sysuid = '-'
_request = get_retry_session()
base_url = f'https://api.agora.io/dev/v2/project/{AGORA_APPID}'
send_url = f'{base_url}/rtm/users/{sysuid}/peer_messages?wait_for_ack=false'


def agora_rtm_send_peer(content, to_uids):
    results = {}
    uid_token = get_rtm_token(sysuid)
    payload = json.dumps(content, cls=DjangoJSONEncoder)
    headers = {'x-agora-token': uid_token, 'x-agora-uid': sysuid}
    for to_uid in to_uids:
        data = {
            "payload": payload,
            "destination": to_uid,
            "enable_offline_messaging": False,
            "enable_historical_messaging": False,
        }
        try:
            resp = _request.post(url=send_url, json=data, headers=headers).json()
            results[to_uid] = resp
        except Exception as exc:
            logger.exception(f'agora_rtm_send_peer__req_error {to_uid}: {str(exc)}')
            results[to_uid] = dict(req_error=str(exc))
    logger.info(f'agora_rtm_send_peer__done {to_uids}: {results}')
    return results
