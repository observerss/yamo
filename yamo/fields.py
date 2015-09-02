#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from enum import Enum
from datetime import datetime

from bson import ObjectId

from .errors import ValidationError, DeserializationError, ArgumentError


# MongoDB will not store dates with milliseconds.
def milli_trim(x):
    return x.replace(
        microsecond=int((x.microsecond / 1000) * 1000))


class BaseField(object):

    """ Base field for all fields. """
    types = []

    def __init__(self, default=None, required=False,
                 nullable=False, name=None):
        self.default = default
        self.required = required
        self.nullable = nullable

        # if None, will be set to assigned name in metaclass
        self.name = name

    def _raise_validation_error(self, value):
        raise ValidationError(self.__class__, self.name, value)

    def validate(self, value):
        if self.required and not self.nullable:
            if value is None:
                self._raise_validation_error(value)
            elif self.types:
                for type_ in self.types:
                    if isinstance(value, type_):
                        break
                else:
                    self._raise_validation_error(value)

    def pre_save_val(self, value):
        """ do something to field value before save """
        return None

    def to_storage(self, value):
        return value

    def to_python(self, value):
        return value


AnyField = BaseField


class ObjectIdField(BaseField):
    types = [ObjectId]


class IntField(BaseField):
    types = [int]

    def __init__(self, min=None, max=None, **kwargs):
        self._min = min
        self._max = max
        super(IntField, self).__init__(**kwargs)

    def validate(self, value):
        super(IntField, self).validate(value)

        if value:
            if (self._min and self._min > value) or \
                    (self._max and self._max < value):
                self._raise_validation_error(value)


class EnumField(BaseField):
    types = [Enum]

    def __init__(self, cls, **kwargs):
        self._cls = cls
        super(EnumField, self).__init__(**kwargs)

    def validate(self, value):
        super(EnumField, self).validate(value)

        if value:
            if not isinstance(value, self._cls):
                self._raise_validation_error(value)

    def to_python(self, value):
        return self._cls(value)

    def to_storage(self, value):
        try:
            return value.value
        except:
            return value


class BooleanField(BaseField):
    types = [bool]


class FloatField(BaseField):
    types = [float, int]


class BinaryField(BaseField):
    types = [bytes]

    def __init__(self, min_bytes=None, max_bytes=None, **kwargs):
        self.min_bytes = min_bytes
        self.max_bytes = max_bytes
        super(BinaryField, self).__init__(**kwargs)

    def validate(self, value):
        super(BinaryField, self).validate(value)
        if value:
            if (self.min_bytes and len(value) < self.min_bytes) or \
                    (self.max_bytes and len(value) > self.max_bytes):
                self._raise_validation_error(value)


class StringField(BaseField):
    types = [str]

    def __init__(self, min_length=None, max_length=None, strip=True, **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        self.strip = strip
        super(StringField, self).__init__(**kwargs)

    def validate(self, value):
        super(StringField, self).validate(value)
        if value:
            if (self.min_length and len(value) < self.min_length) or \
                    (self.max_length and len(value) > self.max_length):
                self._raise_validation_error(value)

    def to_storage(self, value):
        if self.strip and value:
            value = value.strip()
        return value


class EmailField(StringField):
    email_re = re.compile(r'^[\S]+@[\S]+\.[\S]+$')

    def __init__(self, **kwargs):
        super(EmailField, self).__init__(
            min_length=5, max_length=100, **kwargs)

    def validate(self, value):
        super(EmailField, self).validate(value)

        if value and not self.email_re.match(value):
            self._raise_validation_error(value)


class DateTimeField(BaseField):
    types = [datetime]

    def __init__(self, modified=False, created=False, **kwargs):

        self.modified = modified
        self.created = created
        if self.created:
            def _default():
                return datetime.utcnow()
            default = _default
        else:
            default = None

        super(DateTimeField, self).__init__(default=default, **kwargs)

    def pre_save_val(self, value):
        if self.modified:
            return datetime.utcnow()

    def to_python(self, value):
        if value is None or isinstance(value, datetime):
            return value

        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    def to_storage(self, value):
        if value and isinstance(value, datetime):
            return milli_trim(value)
        return value


class DictField(BaseField):
    types = [dict]

    def __init__(self, default=None, **kwargs):
        default = default or {}
        super(DictField, self).__init__(default=default, **kwargs)

    def to_storage(self, value):
        escaped = {}
        for k, v in value.items():
            if isinstance(k, str):
                k = k.replace('.', '__dot__')
            escaped[k] = v
        return escaped

    def to_python(self, value):
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise DeserializationError(self, value)

        unescaped = {}
        for k, v in value.items():
            if isinstance(k, str):
                k = k.replace('__dot__', '.')
            unescaped[k] = v
        return unescaped


class ListField(BaseField):
    types = [list]

    def __init__(self, field=None, default=None, **kwargs):
        default = default or []
        try:
            if issubclass(field, BaseField):
                field = field()
        except:
            pass
        self.field = field
        super(ListField, self).__init__(default=default, **kwargs)

    def validate(self, value):
        super(ListField, self).validate(value)

        if value and self.field:
            for v in value:
                self.field.validate(v)

    def to_storage(self, value):
        if self.field:
            return [self.field.to_storage(v) for v in value]
        else:
            return value

    def to_python(self, value):
        if value is None:
            return []

        if not isinstance(value, list):
            raise DeserializationError(self, value)

        if self.field:
            return [self.field.to_python(v) for v in value]
        else:
            return value


class EmbeddedField(BaseField):

    def __init__(self, embedded=None, **kwargs):
        from yamo import EmbeddedDocument
        if not issubclass(embedded, EmbeddedDocument):
            raise ArgumentError(EmbeddedField, embedded)

        super(EmbeddedField, self).__init__(**kwargs)
        self.embedded = embedded

    def validate(self, value):
        super(EmbeddedField, self).validate(value)

        if value:
            if not isinstance(value, self.embedded):
                self._raise_validation_error(value)
            else:
                value.validate()

    def to_storage(self, value):
        if isinstance(value, dict):
            value = self.embedded(value)

        return getattr(value, '_data', None)

    def to_python(self, value):
        if value:
            return self.embedded(value)


class SequenceField(IntField):

    """ Auto Increment Integer Field """

    def pre_save_val(self, value):
        if value:
            return value

        while True:
            try:
                r = self._doc._db.counters.find_and_modify(
                    query={'_id': self.name},
                    update={'$inc': {'seq': 1}},
                    new=True, upsert=True)
            except:
                continue
            else:
                break
        return r['seq']
