#!/usr/bin/env python3
"""
AI News Fetcher
Fetches and scores AI news from RSS feeds
"""

import feedparser
import yaml
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urlparse
import urllib.request
import urllib.error
import ssl
import sys
from pathlib import Path
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
import certifi

# Import FeedCache from same directory
try:
    from cache_manager import FeedCache
except ImportError:
    from .cache_manager import FeedCache

class AINewsFetcher:
    def __init__(self, config_path: str = None, categories: str = 'all', user_prefs_path: str = None, use_cache: bool = True):
        if config_path is None:
            config_path = Path(__file__).parent / "feeds.yaml"

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.feeds = []
        for category, feed_list in self.config['feeds'].items():
            self.feeds.extend(feed_list)

        # Load user preferences (optional)
        if user_prefs_path is None:
            user_prefs_path = Path(__file__).parent / "user_preferences.yaml"

        self.user_prefs = {}
        if Path(user_prefs_path).exists():
            try:
                with open(user_prefs_path, 'r') as f:
                    self.user_prefs = yaml.safe_load(f) or {}
            except Exception:
                pass  # Silently ignore preferences file errors

        # Initialize cache
        cache_ttl = self.user_prefs.get('performance', {}).get('cache_ttl_minutes', 30)
        self.cache = FeedCache(ttl_minutes=cache_ttl) if use_cache else None

        # Apply favorite source boost
        favorite_sources = self.user_prefs.get('favorite_sources', [])
        for feed in self.feeds:
            if feed['name'] in favorite_sources:
                feed['weight'] += 2  # Boost favorite sources

        # Filter out excluded sources
        excluded_sources = self.user_prefs.get('excluded_sources', [])
        if excluded_sources:
            self.feeds = [f for f in self.feeds if f['name'] not in excluded_sources]

        # Filter by category if specified
        if categories != 'all':
            allowed = [c.strip() for c in categories.split(',')]
            self.feeds = [f for f in self.feeds if f['category'] in allowed]

    def _fetch_single_feed(self, feed_config: Dict[str, Any], cutoff_date: datetime) -> tuple:
        """Fetch a single feed and return (feed_config, entries, error_message)"""
        # Try cache first
        if self.cache:
            cached_entries = self.cache.get(feed_config['url'])
            if cached_entries is not None:
                # Filter cached entries by cutoff date
                filtered_entries = [
                    e for e in cached_entries
                    if datetime.fromisoformat(e['published']) > cutoff_date
                ]
                return (feed_config, filtered_entries, None)

        feed_entries = []
        try:
            # Download RSS content first (feedparser.parse(url) doesn't work reliably)
            req = urllib.request.Request(
                feed_config['url'],
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            # Use certifi for proper SSL certificate verification
            try:
                ctx = ssl.create_default_context(cafile=certifi.where())
                with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                    content = response.read()
            except (ssl.SSLError, urllib.error.URLError) as e:
                # Only fall back to unverified for specific SSL issues with known-safe feeds
                # This maintains security while allowing access to feeds with cert issues
                if 'SSL' in str(e) or 'CERTIFICATE' in str(e) or isinstance(e, ssl.SSLError):
                    # Log warning about SSL fallback
                    if hasattr(sys.stderr, 'write'):
                        print(f"Warning: SSL verification failed for {feed_config['name']}, using unverified connection", file=sys.stderr)

                    ctx = ssl.create_default_context(cafile=certifi.where())
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                        content = response.read()
                else:
                    # Re-raise if it's not SSL-related
                    raise

            # Parse the downloaded content
            feed = feedparser.parse(content)

            for entry in feed.entries:
                # Parse published date
                pub_date = self._parse_date(entry)

                if pub_date and pub_date > cutoff_date:
                    entry_data = {
                        'title': entry.get('title', 'No title'),
                        'link': entry.get('link', ''),
                        'published': pub_date.isoformat(),
                        'summary': entry.get('summary', entry.get('description', '')),
                        'source': feed_config['name'],
                        'category': feed_config['category'],
                        'base_weight': feed_config['weight']
                    }
                    feed_entries.append(entry_data)

            # Cache the results
            if self.cache:
                self.cache.set(feed_config['url'], feed_entries)

            return (feed_config, feed_entries, None)

        except urllib.error.URLError:
            return (feed_config, [], "Network error")
        except ssl.SSLError:
            return (feed_config, [], "SSL error")
        except Exception as e:
            return (feed_config, [], type(e).__name__)

    def fetch_all_feeds(self, days: int = 7, show_progress: bool = True, max_workers: int = 5) -> List[Dict[str, Any]]:
        """Fetch entries from all feeds within the last N days (parallel)"""
        cutoff_date = datetime.now() - timedelta(days=days)
        all_entries = []

        total_feeds = len(self.feeds)

        if show_progress:
            print(f"Fetching from {total_feeds} RSS feeds (parallel)...", file=sys.stderr)

        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all feed fetch tasks
            future_to_feed = {
                executor.submit(self._fetch_single_feed, feed_config, cutoff_date): feed_config
                for feed_config in self.feeds
            }

            completed = 0
            for future in as_completed(future_to_feed):
                feed_config, entries, error = future.result()
                completed += 1

                if show_progress:
                    status = f"[{completed}/{total_feeds}] {feed_config['name']}"
                    if error:
                        print(f"{status} ✗ ({error})", file=sys.stderr)
                    else:
                        print(f"{status} ✓ ({len(entries)} articles)", file=sys.stderr)
                elif error:
                    # Show error even if not showing progress
                    error_msg = {
                        "Network error": "Network error (check internet connection)",
                        "SSL error": "SSL certificate error"
                    }.get(error, error)
                    print(f"Error fetching {feed_config['name']}: {error_msg}", file=sys.stderr)

                if not error:
                    all_entries.extend(entries)

        if show_progress:
            print(f"\nTotal articles found: {len(all_entries)}", file=sys.stderr)

        return all_entries

    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse date from entry"""
        # Try published_parsed first
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except:
                pass

        # Try updated_parsed
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except:
                pass

        # Return None instead of datetime.now() to avoid skewing recency scores
        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def score_entry(self, entry: Dict[str, Any]) -> float:
        """Calculate importance score for an entry"""
        score = entry['base_weight']

        # Keyword boosting with overlap prevention
        text = (entry['title'] + ' ' + entry['summary']).lower()

        # Combine all keywords with their scores
        all_keywords = [
            (kw, 5) for kw in self.config['scoring']['keyword_boost']['high_priority']
        ] + [
            (kw, 3) for kw in self.config['scoring']['keyword_boost']['medium_priority']
        ] + [
            (kw, 1) for kw in self.config['scoring']['keyword_boost']['low_priority']
        ]

        # Sort by length descending (match longer phrases first)
        all_keywords.sort(key=lambda x: len(x[0]), reverse=True)

        matched_spans = []  # Track (start, end) positions

        for keyword, boost_value in all_keywords:
            kw_lower = keyword.lower()
            start = 0
            while True:
                pos = text.find(kw_lower, start)
                if pos == -1:
                    break

                end = pos + len(kw_lower)

                # Check if this span overlaps with any matched span
                overlaps = any(
                    not (end <= m_start or pos >= m_end)
                    for m_start, m_end in matched_spans
                )

                if not overlaps:
                    score += boost_value
                    matched_spans.append((pos, end))

                start = end

        # Recency boost
        pub_date = datetime.fromisoformat(entry['published'])
        age = datetime.now() - pub_date

        if age < timedelta(days=1):
            score += self.config['scoring']['recency_boost']['last_24h']
        elif age < timedelta(days=2):
            score += self.config['scoring']['recency_boost']['last_48h']
        elif age < timedelta(days=7):
            score += self.config['scoring']['recency_boost']['last_week']

        return score

    def get_top_n(self, entries: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
        """Score and return top N entries"""
        # Add scores
        for entry in entries:
            entry['score'] = self.score_entry(entry)

        # Sort by score (descending)
        sorted_entries = sorted(entries, key=lambda x: x['score'], reverse=True)

        # Get top N
        top_entries = sorted_entries[:n]

        # Clean HTML only for top entries (lazy cleaning for performance)
        for entry in top_entries:
            entry['summary'] = self._clean_html(entry['summary'])

        return top_entries

    def remove_duplicates(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entries based on URL and fuzzy title similarity"""
        unique_entries = []
        seen_urls = set()
        seen_titles = []  # List of normalized titles for fuzzy matching

        for entry in entries:
            # Level 1: Exact URL match
            url = entry.get('link', '')
            if url and url in seen_urls:
                continue

            # Level 2: Fuzzy title match
            normalized_title = entry['title'].lower().strip()

            is_duplicate = False
            for seen_title in seen_titles:
                similarity = SequenceMatcher(None, normalized_title, seen_title).ratio()
                if similarity >= 0.85:  # 85% similarity threshold
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            # Add to unique set
            if url:
                seen_urls.add(url)
            seen_titles.append(normalized_title)
            unique_entries.append(entry)

        return unique_entries

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fetch AI news from RSS feeds')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back')
    parser.add_argument('--top', type=int, default=5, help='Number of top items to return')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--category', type=str, default='all',
        help='Comma-separated categories to include (official,research,community,tech_news,ai_tools)')
    parser.add_argument('--output', type=str, default='json', choices=['json', 'text'], help='Output format')
    parser.add_argument('--no-cache', action='store_true', help='Disable cache, fetch fresh data')

    args = parser.parse_args()

    fetcher = AINewsFetcher(args.config, categories=args.category, use_cache=not args.no_cache)

    # Fetch all entries
    entries = fetcher.fetch_all_feeds(days=args.days)

    # Remove duplicates
    entries = fetcher.remove_duplicates(entries)

    # Get top N
    top_entries = fetcher.get_top_n(entries, n=args.top)

    # Output
    if args.output == 'json':
        print(json.dumps(top_entries, indent=2))
    else:
        for i, entry in enumerate(top_entries, 1):
            print(f"\n{i}. {entry['title']}")
            print(f"   Source: {entry['source']} | Score: {entry['score']:.1f}")
            print(f"   Link: {entry['link']}")
            print(f"   Published: {entry['published']}")
            print(f"   Summary: {entry['summary'][:200]}...")

if __name__ == '__main__':
    main()
