"""
https://docs.djangoproject.com/en/3.1/topics/db/multi-db/
"""
import random

from server.constant.djalias import DBAlias


class Router(object):

    def db_for_read(self, model, **hints):
        raise NotImplementedError()

    def db_for_write(self, model, **hints):
        raise NotImplementedError()

    def allow_relation(self, obj1, obj2, **hints):
        raise NotImplementedError()

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        raise NotImplementedError()


class DBMainRouter(Router):
    """ [数据库]路由 """
    def db_for_read(self, model, **hints):
        """
        Reads go to a randomly-chosen replica.
        """
        alias = random.choice([
            DBAlias.Default.value,
            DBAlias.Replica.value,
        ])
        return alias

    def db_for_write(self, model, **hints):
        """
        Writes always go to default.
        """
        return DBAlias.Default.value

    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations between objects are allowed if both objects are
        in the default/replica pool.
        """
        db_list = (
            DBAlias.Default.value,
            DBAlias.Replica.value,
        )
        # noinspection PyProtectedMember
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        All non-auth models end up in this pool.
        """
        is_allow = db == DBAlias.Default.value
        return is_allow
