from enum import Enum, unique


@unique
class DBAlias(Enum):
    """
    Django databases
    """
    Default = 'default'     # 主库 Primary
    Replica = 'replica'     # 从库 Replica


@unique
class CacheAlias(Enum):
    """
    Django caches
    """
    Default = 'default'
    Session = 'session'
    Throttle = 'throttle'


@unique
class CQueueAlias(Enum):
    """
    Celery queues
    """
    Default = 'default'
    Timed = 'timed'


if __name__ == '__main__':
    print(DBAlias.Primary.value)
