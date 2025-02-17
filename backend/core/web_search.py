import time
import json
import logging
from datetime import datetime
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from core.cache import SearchCache
from typing import List, Dict
import asyncio
import random

logger = logging.getLogger(__name__)

class WebSearchClient:
    def __init__(self):
        self.last_request_time = 0
        self.min_delay = 2
        self.base_error_delay = 30
        self.max_error_delay = 120
        self.max_retries = 3
        self.cache = SearchCache()
        self.error_count = 0

    def _get_cache_key(self, query: str, search_type: str) -> str:
        return f"{search_type}:{query}"

    async def _exponential_backoff(self, attempt: int) -> float:
        base_delay = min(
            self.base_error_delay * (2 ** attempt),
            self.max_error_delay
        )
        jitter = random.uniform(0, 0.1 * base_delay)
        return base_delay + jitter

    async def search(self, query: str, search_type='text', num_results: int = 3) -> List[Dict]:
        cache_key = self._get_cache_key(query, search_type)
        if cached := self.cache.get(cache_key):
            logger.info(f"Returning cached results for {query}")
            self.error_count = 0
            return cached[:num_results]

        for attempt in range(self.max_retries):
            try:
                current_time = time.time()
                if (delay := self.min_delay - (current_time - self.last_request_time)) > 0:
                    await asyncio.sleep(delay)

                results = []
                with DDGS() as ddgs:
                    search_func = {
                        'text': ddgs.text,
                        'news': ddgs.news,
                        'images': ddgs.images,
                        'videos': ddgs.videos
                    }.get(search_type)
                    
                    search_results = list(search_func(
                        query,
                        region='wt-wt',
                        safesearch='moderate',
                        **({'timelimit': 'd'} if search_type == 'news' else {}),
                        max_results=num_results
                    )) if search_func else []

                    processor = getattr(self, f"_process_{search_type}_results", None)
                    if processor:
                        results = processor(search_results)

                self.last_request_time = time.time()
                if results:
                    self.cache.set(cache_key, results)
                    self.error_count = 0
                    return results
                return [self._create_empty_result(search_type)]

            except DuckDuckGoSearchException as e:
                logger.error(f"Search error (attempt {attempt+1}/{self.max_retries}): {e}")
                self.error_count += 1
                
                if "Ratelimit" in str(e) and attempt < self.max_retries - 1:
                    backoff_time = await self._exponential_backoff(self.error_count - 1)
                    logger.info(f"Rate limited. Waiting {backoff_time:.1f} seconds before retry...")
                    await asyncio.sleep(backoff_time)
                    continue
                
                return [self._create_rate_limit_result(search_type)]

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return [self._create_error_result(search_type, e)]

    def _process_text_results(self, results):
        return [{
            'type': 'text',
            'title': r.get('title'),
            'link': r.get('href'),
            'snippet': r.get('body')
        } for r in results]

    def _process_news_results(self, results):
        return [{
            'type': 'news',
            'title': r.get('title'),
            'link': r.get('link'),
            'snippet': r.get('body'),
            'date': r.get('date'),
            'source': r.get('source')
        } for r in results]

    def _process_images_results(self, results):
        return [{
            'type': 'image',
            'title': r.get('title'),
            'link': r.get('link'),
            'thumbnail': r.get('thumbnail'),
            'image': r.get('image'),
            'source': r.get('source')
        } for r in results]

    def _process_videos_results(self, results):
        return [{
            'type': 'video',
            'title': r.get('title'),
            'link': r.get('link'),
            'thumbnail': r.get('thumbnail'),
            'duration': r.get('duration'),
            'source': r.get('source')
        } for r in results]

    def _create_empty_result(self, search_type):
        return {
            'type': search_type,
            'title': 'No results found',
            'link': '',
            'snippet': 'No search results were found.'
        }

    def _create_rate_limit_result(self, search_type):
        return {
            'type': search_type,
            'title': 'Search temporarily unavailable',
            'link': '',
            'snippet': 'The search service is currently rate limited. Please wait a moment before trying another search query.'
        }

    def _create_error_result(self, search_type, error):
        return {
            'type': search_type,
            'title': 'Error',
            'link': '',
            'snippet': f'Search failed: {str(error)}'
        }

    async def summarize_results(self, results: List[Dict]) -> str:
        if not results:
            return "No results to summarize"

        try:
            articles_text = "Summarize these results:\n\n" + "\n\n".join(
                f"Result {i+1}:\nTitle: {r['title']}\nContent: {r.get('snippet', '')}"
                for i, r in enumerate(results)
            )

            with DDGS() as ddgs:
                return ddgs.chat(articles_text, model="o3-mini")
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return "Unable to generate summary"

search_client = WebSearchClient()