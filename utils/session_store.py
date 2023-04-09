"""
Module defining session store
"""

import redis

class AbstractSessionStore:
    """
    Abstract data store to define interface
    """
    def get(self, key):
        raise NotImplementedError

    def set(self, key, value):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError
    
    def key_list(self):
        raise NotImplementedError

class InMemoryStore(AbstractSessionStore):
    """
    Class for in memory data store
    """
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def delete(self, key):
        if key in self.store:
            del self.store[key]

    def key_list(self):
        return list(self.store.keys())

class RedisStore(AbstractSessionStore):
    """
    Class for Redis data store
    """
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)

    def get(self, key):
        return self.redis_client.get(key)

    def set(self, key, value):
        self.redis_client.set(key, value)

    def delete(self, key):
        self.redis_client.delete(key)

    def key_list(self):
        return self.redis_client.keys('*')
