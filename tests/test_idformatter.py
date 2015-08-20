from yamo import *

class Q(Document):
    class Meta:
        idf = IDFormatter('{int1}')
    oid = ObjectIdField()
    int1 = IntField(min=2, max=5, default=3)


Connection().register_all()

def test_idformatter():
    Q.drop()
    q = Q({'int1': 3})
    q.save()
    assert q._id == '3'
    q = Q.query_one()
    assert q._id == '3'



if __name__ == '__main__':
    test_idformatter()
