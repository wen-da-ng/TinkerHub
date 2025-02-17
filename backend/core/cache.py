from cachetools import TTLCache
from typing import List, Dict, Optional

class SearchCache:
    def __init__(self, ttl: int = 3600):
        self.cache = TTLCache(maxsize=100, ttl=ttl)

    def get(self, key: str) -> Optional[List[Dict]]:
        return self.cache.get(key)

    def set(self, key: str, value: List[Dict]):
        self.cache[key] = value