import time
import queue
import pickle
import functools
import threading


task = queue.Queue()
prepared = {}


def myopen(oldopen, conn):
    task.put(conn)
    return oldopen()


def bg_prepare(started=[]):
    def _prepare(prepared={}):
        while True:
            try:
                conn = task.get(timeout=1)
                for doc in conn.docdb:
                    if doc not in prepared:
                        doc.prepare()
                        prepared[doc] = True
            except queue.Empty:
                pass
    if not started:
        started.append(1)
        threading.Thread(target=_prepare, daemon=True).start()


bg_prepare()


class Connection(object):

    """ MongoDB MongoClient Wrapper

    >>> class Post(Document):
    ...     pass
    >>> conn = Connection(host="localhost", port=27017)
    >>> conn.register(Post)
    """
    # Document -> DB
    docdb = {}

    # host, port, *args, **kwargs -> mongoclient
    mcs = {}

    def __init__(self, host=None, port=None, db=None, *args, **kwargs):
        # in case pymongo is not installed when setup yamo
        import pymongo
        if host and '/' in host:
            host, db = host.rsplit('/', 1)
        if not db:
            db = 'test'

        kwargs['connect'] = False
        key = pickle.dumps((host, port, db, args, kwargs))
        if key not in self.mcs:
            self.client = pymongo.MongoClient(host, port, *args, **kwargs)
            self.mcs[key] = self.client
        else:
            self.client = self.mcs[key]
        oldopen = self.client._topology.open
        self.client._topology.open = functools.partial(
            myopen, oldopen=oldopen, conn=self)
        self.db = self.client[db]

    def register_all(self):
        self.register(*self.docdb.keys())

    def register(self, *docs):
        for doc in docs:
            self._register(doc)

    def _register(self, doc):
        try:
            doc._db
        except:
            self.docdb[doc] = self.db
            doc._db = self.db
        else:
            self.docdb[doc] = doc._db
