"""
Module defining session store
"""

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
        # logging.debug("[%s] Server - Storage - Setting InMemory data store %s:%s", SERVER_NAME, key, value)
    
    def delete(self, key):
        if key in self.store:
            del self.store[key]
            # logging.debug("[%s] Server - Storage - Deleting InMemory data store for %s", SERVER_NAME, key)