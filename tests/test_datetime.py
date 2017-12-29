from yamo import *
from datetime import datetime


class Q(Document):
    class Meta:
        idx1 = Index('u', unique=True)
    u = IntField()
    d = DateTimeField()
    t = StringField()


Connection().register_all()


def test_datetime():
    Q({'u': 1, 't': 'haha', 'd': datetime(2015, 1, 1)}).upsert()
    p = Q.query_one({'u': 1})
    assert p.d == datetime(2015, 1, 1)
    assert p.t == 'haha'
    Q({'u': 1, 't': 'hehe'}).upsert()
    p = Q.query_one({'u': 1})
    assert p.t == 'hehe'
    assert p.d == datetime(2015, 1, 1)
    Q.drop()


if __name__ == '__main__':
    test_datetime()
