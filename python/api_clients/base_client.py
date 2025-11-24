"""
Base client for distributor APIs with caching, rate limiting, and error handling
"""
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import aiohttp
from abc import ABC, abstractmethod


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a request token is available"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens based on time elapsed
            self.tokens = min(
                self.requests_per_minute,
                self.tokens + (elapsed * self.requests_per_minute / 60.0)
            )
            self.last_update = now

            # If no tokens available, wait
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * 60.0 / self.requests_per_minute
                await asyncio.sleep(wait_time)
                self.tokens = 1

            self.tokens -= 1


class CacheEntry:
    """Cache entry with TTL"""

    def __init__(self, data: Any, ttl_seconds: int = 3600):
        self.data = data
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class APICache:
    """Simple in-memory cache with TTL"""

    def __init__(self, default_ttl: int = 3600):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        async with self.lock:
            entry = self.cache.get(key)
            if entry and not entry.is_expired():
                return entry.data
            elif entry:
                # Remove expired entry
                del self.cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value with TTL"""
        async with self.lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = CacheEntry(value, ttl)

    async def clear(self):
        """Clear all cached entries"""
        async with self.lock:
            self.cache.clear()


class BaseDistributorClient(ABC):
    """Base class for distributor API clients"""

    def __init__(
        self,
        rate_limit: int = 30,
        cache_ttl: int = 3600,
        use_mock: bool = False
    ):
        self.rate_limiter = RateLimiter(rate_limit)
        self.cache = APICache(cache_ttl)
        self.session: Optional[aiohttp.ClientSession] = None
        self.use_mock = use_mock

    async def __aenter__(self):
        """Async context manager entry"""
        # Use TCPConnector with Windows-compatible settings
        connector = aiohttp.TCPConnector(
            force_close=True,  # Fix Windows socket reuse issues
            enable_cleanup_closed=True  # Clean up closed connections
        )
        self.session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Make GET request with rate limiting and caching

        Args:
            url: Request URL
            headers: Optional request headers
            params: Optional query parameters
            use_cache: Whether to use cache (default: True)

        Returns:
            JSON response as dict

        Raises:
            aiohttp.ClientError: On HTTP errors
        """
        # Check cache first
        if use_cache:
            cache_key = f"{url}:{str(params)}"
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Rate limit
        await self.rate_limiter.acquire()

        # Make request
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with context manager.")

        async with self.session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            data = await response.json()

        # Cache result
        if use_cache:
            await self.cache.set(cache_key, data)

        return data

    async def _post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Make POST request with rate limiting

        Args:
            url: Request URL
            headers: Optional request headers
            params: Optional query parameters
            json_data: Optional JSON body
            use_cache: Whether to cache result (default: False)

        Returns:
            JSON response as dict
        """
        # Check cache first
        if use_cache:
            cache_key = f"{url}:{str(params)}:{str(json_data)}"
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Rate limit
        await self.rate_limiter.acquire()

        # Make request
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with context manager.")

        async with self.session.post(url, headers=headers, params=params, json=json_data) as response:
            response.raise_for_status()
            data = await response.json()

        # Cache result if requested
        if use_cache:
            await self.cache.set(cache_key, data)

        return data

    @abstractmethod
    async def search_by_mpn(self, mpn: str) -> Dict[str, Any]:
        """
        Search for component by manufacturer part number

        Args:
            mpn: Manufacturer part number

        Returns:
            Component data as dict
        """
        pass

    @abstractmethod
    async def get_component_details(self, part_id: str) -> Dict[str, Any]:
        """
        Get detailed component information

        Args:
            part_id: Distributor's part ID

        Returns:
            Detailed component data
        """
        pass

    @abstractmethod
    async def search_by_keyword(self, keyword: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search for components by keyword with optional filters

        Args:
            keyword: Search keyword
            filters: Optional search filters (category, manufacturer, etc.)

        Returns:
            Search results
        """
        pass
