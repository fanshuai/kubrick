from django.conf import settings
from django.core.cache import caches

from django.core.management.base import BaseCommand
from server.constant.djalias import CacheAlias


class Command(BaseCommand):
    """
    python manage.py clearcache --alias=all
    python manage.py clearcache --alias=default,session
    """

    all_cache_alias = list(
        val.value for val in CacheAlias.__members__.values()
    )
    clear_ignore_caches = {
        CacheAlias.Throttle.value,
    }

    @classmethod
    def is_ignore(cls, key):
        return key in cls.clear_ignore_caches

    def add_arguments(self, parser):
        parser.add_argument('--alias', type=str, dest='cache_alias', action='append')

    def handle(self, *args, **options):
        print(self.all_cache_alias)
        caches_keys = settings.CACHES.keys()
        cache_alias = options['cache_alias']
        if cache_alias is None:
            self.stdout.write(self.style.NOTICE('please choice alias like `--alias=all`'))
            for idx, val in enumerate(self.all_cache_alias):
                self.stdout.write(self.style.WARNING('[%s] %s' % (idx + 1, val)))
        elif isinstance(cache_alias, list):
            if cache_alias == ['all']:
                clear_alias = self.all_cache_alias
            else:
                clear_alias = ','.join(cache_alias).split(',')
            for key in clear_alias:
                if self.is_ignore(key):
                    self.stdout.write(self.style.WARNING(f'cache [{key}] ignored!'))
                    continue
                if key not in caches_keys:
                    self.stdout.write(self.style.WARNING(f'cache [{key}] does not exists!'))
                    continue
                caches[key].clear()
                self.stdout.write(self.style.SUCCESS(f'cache [{key}] cleared ~'))
        else:
            self.stdout.write(self.style.WARNING(f'cache alias [{str(cache_alias)}] does not support!!'))
