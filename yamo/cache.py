#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import types
import pickle
import functools


from pymongo.cursor import Cursor


class CachedModel(object):

    """ Used in Model.cached

    :param timeout: timeout in seconds
    :param cache_none: whether to cache None results
    """
    # cls -> (cache_time, value)
    caches = {}

    def __init__(self, cls, timeout=300, cache_none=False):
        self.cls = cls
        self.timeout = timeout
        self.cache_none = cache_none
        self.count = 0
        if self.cls not in self.caches:
            self.caches[self.cls] = {}

    def _clear_timeout(self):
        cache = self.caches[self.cls]
        now = time.time()
        invals = []
        for key, values in cache.items():
            if values[0] < now - self.timeout:
                invals.append(key)
        for key in invals:
            del cache[key]

    def __getattr__(self, name):
        self.count += 1
        if self.count % 1000 == 0:
            self._clear_timeout()

        attr = getattr(self.cls, name)
        if callable(attr):
            # wrap this callable to use cache
            @functools.wraps(attr)
            def deco(*args, **kwargs):
                cache = self.caches[self.cls]
                key = pickle.dumps([attr.__name__, args, kwargs])
                cache_miss = key not in cache

                def timedout():
                    return cache[key][0] < time.time() - self.timeout

                if cache_miss or timedout():
                    value = attr(*args, **kwargs)
                    if isinstance(value, Cursor) or \
                            isinstance(value, types.GeneratorType):
                        # this will consume A LOT of memory, use with care
                        value = list(value)
                    if value is not None or self.cache_none:
                        cache[key] = (time.time(), value)
                    else:
                        return
                return cache[key][1]
            return deco
        else:
            return attr
