import os
from abc import ABC
from django.conf import settings
from oss2 import OBJECT_ACL_PUBLIC_READ
from django_oss_storage.backends import OssStorage, logger

from kubrick.initialize import ALIOSS_CDN_HOST_URL


class CDNOssStorage(OssStorage, ABC):
    """ 使用CDN域名的 OssStorage """

    def _save(self, name, content):
        target_name = self._get_key_name(name)
        headers = {'x-oss-object-acl': OBJECT_ACL_PUBLIC_READ}
        logger().debug(f'target name: {target_name} \ncontent: {content}')
        self.bucket.put_object(target_name, content, headers=headers)
        return os.path.normpath(name)

    def url(self, name):
        key = self._get_key_name(name)
        val = f'{ALIOSS_CDN_HOST_URL}/{key}'
        return val


class CDNOssMediaStorage(CDNOssStorage, ABC):
    """ 使用CDN域名的 OssMediaStorage """

    def __init__(self):
        self.location = settings.MEDIA_URL
        logger().debug("locatin: %s", self.location)
        super().__init__()
