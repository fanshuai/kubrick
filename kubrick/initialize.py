import os
import socket
import logging

from server.corelib import yamload


logging.basicConfig(
    level=logging.INFO, format='[%(asctime)s:%(process)5d]:%(levelname)s:%(name)s::%(message)s'
)


PID = os.getpid()
HOST_NAME = socket.gethostname()

RUN_ENV = str(os.getenv('RUN_ENV', 'DEV')).upper()
RUN_ENV_LOWER = RUN_ENV.lower()
IS_PROD_ENV = RUN_ENV == 'PROD'
IS_DEV_ENV = RUN_ENV == 'DEV'
IS_SIT_ENV = RUN_ENV == 'SIT'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAVICON_IMG = os.path.join(BASE_DIR, 'frontend', 'public', 'favicon.png')
QRIMG_LOGO = os.path.join(BASE_DIR, 'frontend', 'public', 'qrimg-logo.png')

CONFIG_DIR = os.path.join(BASE_DIR, 'config', 'envs')

CONFIG_PATH_ENV = os.path.join(CONFIG_DIR, 'kubrick-%s.yml' % RUN_ENV_LOWER)
logging.info(f'[{RUN_ENV}] [{HOST_NAME}] [CONFIG:{CONFIG_PATH_ENV}]')

CONFIG = yamload.ConfigLoader(cfg_path=CONFIG_PATH_ENV).get
VERSION, IS_DEBUG = CONFIG('VERSION'), CONFIG('DJANGO.DEBUG')
ENV_PREFIX = f'[{RUN_ENV}:{VERSION}:{HOST_NAME}]'
IS_DJADMIN = 'djadmin' in os.environ.get('DJANGO_SETTINGS_MODULE', '')

logging.info(f'[{RUN_ENV}] [{HOST_NAME}] [DEBUG:{IS_DEBUG}]')

LOGS_DIR = CONFIG('DIRS.LOGS_API')
SILKY_DIR = CONFIG('DIRS.SILKY')
TEMP_DIR = CONFIG('DIRS.TEMP')

SENTRY_DSN = CONFIG('SENTRY_DSN')

API_HOST = CONFIG('DJANGO.API_HOST')
QRIMG_HOST = CONFIG('DJANGO.QRIMG_HOST')

SUPPORT_EMAIL = 'support@ifand.com'


AGORA_APPID = CONFIG('AGORA.APPID')
AGORA_CERTIFICATE = CONFIG('AGORA.CERTIFICATE')


ALIYUN_AK = CONFIG('ALIYUN.AK')
ALIYUN_SECRET = CONFIG('ALIYUN.SECRET')
ALIYUN_RAMUSR = CONFIG('ALIYUN.RAMUSR')

ALIOSS_BUCKET_NAME = CONFIG('ALIOSS.BUCKET_NAME')
ALIOSS_ENDPOINT_PUBLIC = CONFIG('ALIOSS.ENDPOINT_PUBLIC')
ALIOSS_ENDPOINT_INTERNAL = CONFIG('ALIOSS.ENDPOINT_INTERNAL')
ALIOSS_CDN_HOST_URL = CONFIG('ALIOSS.CDN_HOST_URL')

DEFAULT_AVATAR = os.path.join(BASE_DIR, 'frontend', 'public', 'avatar.png')
DEFAULT_AVATAR_OSS = 'https://oss.mowo.co/assets/avatar.png'


if __name__ == '__main__':
    import json
    all_config = CONFIG()
    print(json.dumps(all_config, indent=2))
