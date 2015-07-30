#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from collections import OrderedDict

from .fields import BaseField
from .errors import ArgumentError
from .connection import Connection

log = logging.getLogger('yamo')


class EmbeddedDocumentType(type):

    """
    This is a type that generates EmbeddedDocument classes properly,
    setting their attributes not to be instances of Field, but rather an
    API for MongoDB itself.
    """

    @staticmethod
    def get_maker(attr):
        def getter(self, attr=attr):
            return self._fields[attr].to_python(self._data.get(attr))

        return getter

    @staticmethod
    def set_maker(attr):
        def setter(self, val=None, attr=attr):
            self._data[attr] = self._fields[attr].to_storage(val)

        return setter

    def __new__(cls, name, bases, dct):
        dct.setdefault('_fields', {})

        for x in bases:
            dct['_fields'].update(getattr(x, '_fields', {}))

        for attr, val in dct.items():
            if isinstance(val, BaseField):
                val.name = attr
                dct['_fields'][attr] = val
                dct[attr] = property(cls.get_maker(attr),
                                     cls.set_maker(attr))

        new_cls = super(EmbeddedDocumentType, cls).__new__(
            cls, name, bases, dct)
        return new_cls


class DocumentType(EmbeddedDocumentType):

    """
    This is a type that generates Document classes properly, setting their
    attributes not to be instances of Field, but rather an API for MongoDB
    itself.
    """
    def __new__(cls, name, bases, dct):
        def build_meta(val):
            val._indexes = []
            val._shardkey = None
            val._formatter = None
            for k, v in val.__dict__.items():
                if k not in ['__weakref__', '__doc__',
                             '__dict__', '__module__']:
                    if isinstance(v, Index):
                        val._indexes.append(v)
                    elif isinstance(v, ShardKey):
                        val._shardkey = v
                    elif isinstance(v, IDFormatter):
                        val._formatter = v

            if not hasattr(val, '__collection__'):
                setattr(val, '__collection__', name.lower())

        if '_id' not in dct:
            def idgetter(self):
                return self._data.get('_id')

            def idsetter(self, val):
                self._data['_id'] = val

            dct['_id'] = property(idgetter, idsetter)

        if 'Meta' not in dct:
            class Meta:
                pass
            dct['Meta'] = Meta
        elif not type(dct['Meta']) is type:
            raise ArgumentError(name, dct['Meta'])

        build_meta(dct['Meta'])

        new_cls = super(DocumentType, cls).__new__(cls, name, bases, dct)

        # setting up connection hook
        Connection.docdb[new_cls] = None
        return new_cls


class Index(object):

    """ Index for Document

    >>> class Post(Document):
    ...    class Meta:
    ...        idx1 = Index('created_at')
    ...        Index(['author', 'tag'], sparse=True)
    ...    pass
    """

    def __init__(self, keys, **kwargs):
        """ MongoDB Index

        Takes either a single key or a list of (key, direction) pairs.
        The key(s) must be an instance of :class:`basestring`
        (:class:`str` in python 3), and the direction(s) must be one of
        (:data:`~pymongo.ASCENDING`, :data:`~pymongo.DESCENDING`,
        :data:`~pymongo.GEO2D`, :data:`~pymongo.GEOHAYSTACK`,
        :data:`~pymongo.GEOSPHERE`, :data:`~pymongo.HASHED`,
        :data:`~pymongo.TEXT`)

        Valid kwargs include, but are not limited to:

          - `name`: custom name to use for this index - if none is
            given, a name will be generated.
          - `unique`: if ``True`` creates a uniqueness constraint on the index.
          - `background`: if ``True`` this index should be created in the
            background.
          - `sparse`: if ``True``, omit from the index any documents that lack
            the indexed field.
          - `bucketSize`: for use with geoHaystack indexes.
            Number of documents to group together within a certain proximity
            to a given longitude and latitude.
          - `min`: minimum value for keys in a :data:`~pymongo.GEO2D`
            index.
          - `max`: maximum value for keys in a :data:`~pymongo.GEO2D`
            index.
          - `expireAfterSeconds`: <int> Used to create an expiring (TTL)
            collection. MongoDB will automatically delete documents from
            this collection after <int> seconds. The indexed field must
            be a UTC datetime or the data will not expire.

        see pymongo's create_index function
        """
        if isinstance(keys, str):
            keys = [keys]
        self.keys = []
        for key in keys:
            if isinstance(key, str):
                self.keys.append((key, 1))
            elif isinstance(key, tuple) and len(key) == 2:
                self.keys.append(key)
            else:
                raise ArgumentError(Index, keys)
        self.kwargs = kwargs
        self.kwargs['background'] = True


class ShardKey(object):

    """ ShardKey for Document

    >>> class Post(Document):
    ...     class Meta:
    ...         ShardKey([('author', 'hash')])

    """

    def __init__(self, keys):
        if isinstance(keys, str):
            keys = [keys]

        self.key = OrderedDict()
        for key in keys:
            if isinstance(key, str):
                key = (key, 1)
            self.key[key[0]] = key[1]


class IDFormatter(object):

    """ IDFormatter for Document

    >>> class Post(Document):
    ...     class Meta:
    ...         IDFormatter('{author}_{pid}')

    can also use a callable function
    """

    def __init__(self, tmpl_or_cb):
        if callable(tmpl_or_cb):
            self._format = tmpl_or_cb
        elif isinstance(tmpl_or_cb, str):
            def _format(**kwargs):
                return tmpl_or_cb.format(**kwargs)
            self._format = _format
        else:
            raise ArgumentError(IDFormatter, tmpl_or_cb)
