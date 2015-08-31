#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from functools import partialmethod

from pymongo.operations import UpdateOne, InsertOne

from .cache import CachedModel
from .errors import ConfigError, ArgumentError
from .metatype import DocumentType, EmbeddedDocumentType

log = logging.getLogger('yamo')


class classproperty(object):

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class MongoOperationMixin(object):

    """ Mongodb raw operations """
    @classmethod
    def run_command(cls, *args, **kwargs):
        cmd = kwargs['cmd']
        del kwargs['cmd']
        return getattr(cls._coll, cmd)(*args, **kwargs)

    for cmd in [
        'insert_one', 'insert_many',

        'find', 'find_one', 'find_one_and_delete',
        'find_one_and_replace', 'find_one_and_update',

        'update_one', 'update_many', 'replace_one',

        'delete_one', 'delete_many',

        'create_index', 'create_indexes', 'reindex',
        'index_information', 'list_indexes',

        'drop', 'drop_index', 'drop_indexes',

        'aggregate', 'group', 'inline_map_reduce', 'map_reduce',

        'bulk_write',
        'initialize_ordered_bulk_op', 'initialize_unordered_bulk_op',

        'rename', 'count', 'distinct', 'options', 'with_options',
    ]:
        locals()[cmd] = partialmethod(run_command, cmd=cmd)


class InitMixin(object):
    def __init__(self, data=None):
        self._data = {}
        self._defaults = {}
        if data:
            for name, field in self._fields.items():
                if name in data:
                    value = data[name]
                else:
                    value = field.default
                    if callable(value):
                        value = value()
                    if value is not None:
                        self._defaults[name] = value

                value = field.to_storage(value)
                self._data[name] = value


class ValidationMixin(object):

    def validate(self):
        for name, field in self._fields.items():
            value = field.to_python(self._data.get(name))
            field.validate(value)

    def to_dict(self):
        d = {}
        for name, field in self._fields.items():
            value = field.to_python(self._data.get(name))
            if isinstance(value, list):
                ovalue, value = value, []
                for v in ovalue:
                    if isinstance(v, EmbeddedDocument):
                        v = v.to_dict()
                    value.append(v)
            d[name] = value
        return d


class MetaMixin(object):

    """ helper methods for "Meta" info """

    @classproperty
    def unique_fields(cls):
        names = set()
        for idx in cls.Meta._indexes or []:
            if idx.kwargs.get('unique'):
                for key in idx.keys:
                    if isinstance(key, tuple):
                        names.add(key[0])
                    else:
                        names.add(key)
        return names

    @classmethod
    def prepare(cls):
        cls.ensure_indexes()
        cls.ensure_shards()

    @classmethod
    def ensure_indexes(cls):
        allowed_keys = set(['name', 'unique', 'background', 'sparse',
                            'bucketSize', 'min', 'max', 'expireAfterSeconds'])
        for idx in cls.Meta._indexes or []:
            if set(idx.kwargs.keys()) - allowed_keys:
                raise ArgumentError(MetaMixin.ensure_indexes, idx.kwargs)

            cls._coll.create_index(idx.keys, **idx.kwargs)

    @classmethod
    def ensure_shards(cls):
        if cls.Meta._shardkey:
            admin = cls._conn.admin
            dbname = cls._db.name
            try:
                admin.command('enableSharding', dbname)
            except Exception as e:
                if 'already' in e:
                    try:
                        admin.command(
                            'shardCollection',
                            '{}.{}'.format(dbname,
                                           cls.Meta.__collection__),
                            key=cls.Meta._shardkey.key)
                    except Exception as e:
                        if 'already' not in e:
                            log.warning('shard collection failed: '
                                        '{}'.format(str(e)))
                else:
                    log.warning('enable shard failed: '
                                '{}'.format(str(e)))


class MapperMixin(object):

    """ ORM only method mixins """

    def refresh(self):
        _id = self._data.get('_id')
        self._data = {}
        if _id:
            doc = self._coll.find_one({'_id': _id})
            if doc:
                self._data = doc
                self.validate()

    @classmethod
    def query(cls, *args, **kwargs):
        """ Same as collection.find, but return Document then dict """
        for doc in cls._coll.find(*args, **kwargs):
            yield cls.from_storage(doc)

    @classmethod
    def query_one(cls, *args, **kwargs):
        """ Same as collection.find_one, but return Document then dict """
        doc = cls._coll.find_one(*args, **kwargs)
        if doc:
            return cls.from_storage(doc)


    def update(self, update):
        """ Update self """
        self._coll.update_one({'_id': self._data['_id']},
                              update)

    def upsert(self, null=False):
        """ Insert or Update Document

        :param null: whether update null values
        Wisely select unique field values as filter,
        Update with upsert=True
        """
        self._pre_save()
        self.validate()

        filter_ = self._upsert_filter()
        if filter_:
            update = self._upsert_update(filter_, null)

            if update['$set']:
                r = self._coll.find_one_and_update(filter_, update,
                                                   upsert=True, new=True)
                self._data['_id'] = r['_id']
        else:
            r = self._coll.insert_one(self._data)
            self._data['_id'] = r.inserted_id

    def save(self):
        self._pre_save()
        self._ensure_id()
        self.validate()

        if '_id' in self._data:
            doc = self._data.copy()
            del doc['_id']
            self._coll.update_one({'_id': self._data['_id']},
                                  {'$set': doc},
                                  upsert=True)
        else:
            self._coll.insert_one(self._data)

    @classmethod
    def bulk_upsert(cls, docs, null=False):
        requests = []
        for doc in docs:
            if not isinstance(doc, cls):
                raise ArgumentError(cls, docs)
            doc.validate()
            filter_ = doc._upsert_filter()
            if filter_:
                update = doc._upsert_update(filter_, null)
                if update['$set']:
                    requests.append(UpdateOne(filter_, update, upsert=True))
            else:
                requests.append(InsertOne(doc._data))
        r = cls._coll.bulk_write(requests, ordered=False)
        return r.upserted_count

    def remove(self):
        _id = self._ensure_id()
        if _id:
            self._coll.delete_one({'_id': _id})
        else:
            log.warning("This document has no _id, it can't be deleted")

    @classmethod
    def cached(cls, timeout=60, cache_none=False):
        """ Cache queries

        :param timeout: cache timeout
        :param cache_none: cache None result

        Usage::

        >>> Model.cached(60).query({...})
        """
        return CachedModel(cls=cls, timeout=timeout, cache_none=cache_none)

    def _pre_save(self):
        for name, field in self._fields.items():
            value = field.pre_save_val(self._data.get(name))
            if value:
                setattr(self, name, value)
            if not field.required and name in self._data \
                    and self._data[name] is None:
                del self._data[name]


    def _upsert_filter(self):
        filter_ = {}
        if self._ensure_id():
            filter_['_id'] = self._data['_id']
        for name in self.unique_fields:
            value = self._data.get(name)
            if value:
                filter_[name] = value
        return filter_

    def _upsert_update(self, filter_, null=False):
        to_update = {}
        to_insert = {}
        for key, value in self._data.items():
            if key not in filter_ and (null or value is not None):
                if self._defaults.get(key) == value:
                    # default value should only been applied if it is an insert
                    to_insert[key] = value
                else:
                    to_update[key] = value
        update = {'$set': to_update}
        if to_insert:
            update['$setOnInsert'] = to_insert
        return update

    def _ensure_id(self):
        _id = self._data.get('_id')
        if not _id and self.Meta._formatter:
            try:
                _id = self.Meta._formatter._format(**self._data)
            except KeyError:
                pass
            else:
                self._data['_id'] = _id
        return _id


class EmbeddedDocument(InitMixin, ValidationMixin,
                       metaclass=EmbeddedDocumentType):
    pass


class Document(InitMixin, ValidationMixin, MetaMixin, MapperMixin, MongoOperationMixin,
               metaclass=DocumentType):

    @classmethod
    def from_storage(cls, data):
        instance = cls()
        instance._data = data
        return instance

    @classproperty
    def _db(cls):
        raise ConfigError('Database not registered, did you run '
                          'conn.register_all()?')

    @classproperty
    def _coll(cls):
        return cls._db[cls.Meta.__collection__]

    def _get_db(self):
        return self._db

    def _get_coll(self):
        return self._coll
