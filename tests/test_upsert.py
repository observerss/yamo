from yamo import *

class P(Document):
    class Meta:
        idx1 = Index('b', unique=True)
    a = StringField()
    b = StringField(default='', required=True)
    c = StringField(required=True, nullable=True)


class Q(Document):
    _id = IntField()
    a = IntField(default=0)
    b = StringField()


Connection().register_all()


def test_upsert():
    P({'b': '5', 'c': '2'}).upsert()
    p = P.query_one({'b': '5'})
    assert p.c == '2'
    P({'b': '5'}).upsert(null=False)
    p = P.query_one({'b': '5'})
    assert p.c == '2'
    P({'b': '5'}).upsert(null=True)
    p = P.query_one({'b': '5'})
    assert p.c is '2'
    P.drop()

def test_default_with_upsert():
    Q.drop()
    q = Q({'_id': 1, 'a': 3, 'b': '3'})
    q.upsert()
    q.refresh()
    assert q.a == 3
    assert q.b == '3'
    q = Q({'_id': 1, 'b': '4'})
    q.upsert()
    q.refresh()
    assert q.a == 3
    assert q.b == '4'



if __name__ == '__main__':
    test_upsert()
    test_default_with_upsert()
