from yamo import *


class E(EmbeddedDocument):
    a = StringField()
    b = StringField()


class Q(Document):
    es = ListField(EmbeddedField(E))


Connection().register_all()


def test_embedded():
    Q.drop()
    q = Q({'es': [{'a': 'a', 'b': 'b'}]})
    q.save()


if __name__ == '__main__':
    test_embedded()
