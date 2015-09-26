import pymongo


class Connection(object):

    """ MongoDB MongoClient Wrapper

    >>> class Post(Document):
    ...     pass
    >>> conn = Connection(host="localhost", port=27017)
    >>> conn.register(Post)
    """
    # Document -> DB
    docdb = {}

    def __init__(self, host=None, port=None, db=None, *args, **kwargs):
        if host and '/' in host:
            db = host.rsplit('/', 1)[-1]
        if not db:
            db = 'test'

        self.client = pymongo.MongoClient(host, port, *args, **kwargs)
        self.db = self.client[db]

    def register_all(self):
        self.register(*self.docdb.keys())

    def register(self, *docs):
        for doc in docs:
            self._register(doc)

    def _register(self, doc):
        if doc not in self.docdb:
            self.docdb[doc] = self.db
            doc._db = self.db
            doc.prepare()
