from pymongo.errors import DuplicateKeyError
from nose.tools import assert_raises

from yamo import (
    Document, Connection,
    IntField, StringField,
    Index,
)


class Test(Document):

    class Meta:
        tsidx = Index(['text', 'status'], unique=True)

    text = StringField(required=True)
    status = IntField()
    count = IntField(default=0)


conn = Connection('mongodb://localhost/yamotest')
conn.register_all()


def test_crud():
    Test.drop()

    t = Test({'text': 'aaa', 'status': 2})
    t.save()

    assert t.count == 0
    assert t._id

    t2 = Test({'text': 'aaa', 'status': 2, 'count': 5})
    t2.upsert()
    assert t2.count == 5
    assert t2._id == t._id

    t2.remove()
    t2.refresh()
    assert t2._id is None


if __name__ == '__main__':
    test_crud()
