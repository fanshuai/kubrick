from kubrick.settings import *

DEBUG = IS_DEBUG
LOGIN_URL = 'admin:login'
ROOT_URLCONF = 'kubrick.djadmin.urls'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  #
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'silk.middleware.SilkyMiddleware',  # Profiling, depend: user auth
]

CSRF_USE_SESSIONS = True


# https://drf-yasg.readthedocs.io/en/stable/security.html
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'X-Token',
            'in': 'header'
        },
    },
}


print(f'=====> [{RUN_ENV}] Django admin {HOST_NAME} {DEBUG} ...')
