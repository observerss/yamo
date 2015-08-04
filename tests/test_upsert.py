from yamo import *

class P(Document):
    class Meta:
        idx1 = Index('b', unique=True)
    a = StringField()
    b = StringField(default='', required=True)
    c = StringField(required=True, nullable=True)


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
    assert p.c is None


if __name__ == '__main__':
    test_upsert()
