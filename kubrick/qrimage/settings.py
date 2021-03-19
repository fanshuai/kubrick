from kubrick.settings import *

DEBUG = False
ROOT_URLCONF = 'kubrick.qrimage.urls'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    #########################
    'server.applibs.abasepp',
    'server.applibs.account',
    'server.applibs.billing',
    'server.applibs.monitor',
    'server.applibs.outside',
    'server.applibs.release',
    'server.applibs.convert',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  #
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


print(f'=====> [{RUN_ENV}] Django qrimage {HOST_NAME} {DEBUG} ...')
