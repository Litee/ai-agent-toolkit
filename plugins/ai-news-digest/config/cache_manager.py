#!/usr/bin/env python3
"""
Simple file-based cache for RSS feed data
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

class FeedCache:
    """Simple file-based cache for RSS feed data"""

    def __init__(self, cache_dir: str = None, ttl_minutes: int = 30):
        """
        Args:
            cache_dir: Directory to store cache files
            ttl_minutes: Cache time-to-live in minutes (default: 30)
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent / '.cache'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(minutes=ttl_minutes)

    def _get_cache_key(self, feed_url: str) -> str:
        """Generate cache key from feed URL"""
        return hashlib.md5(feed_url.encode()).hexdigest()

    def get(self, feed_url: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached feed data if available and not expired"""
        cache_key = self._get_cache_key(feed_url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)

            # Check expiration
            cached_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cached_time > self.ttl:
                return None  # Expired

            return cached_data['entries']
        except Exception:
            return None

    def set(self, feed_url: str, entries: List[Dict[str, Any]]):
        """Cache feed data"""
        cache_key = self._get_cache_key(feed_url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        cached_data = {
            'cached_at': datetime.now().isoformat(),
            'feed_url': feed_url,
            'entries': entries
        }

        try:
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f)
        except Exception:
            # Fail silently if can't cache
            pass

    def clear(self):
        """Clear all cached data"""
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                cache_file.unlink()
            except Exception:
                pass  # Ignore errors during cleanup
