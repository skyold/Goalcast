from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
import httpx
from goalcast.utils.logger import logger
from goalcast.utils.rate_limiter import get_rate_limiter


class BaseProvider(ABC):
    BASE_URL: str = ""
    DEFAULT_TIMEOUT: float = 10.0
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

    def __init__(self, api_key: str = "", timeout: float = None):
        self.api_key = api_key
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = None

    def _get_rate_limiter_name(self) -> str:
        return self.name

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
    ) -> Optional[Dict[str, Any]]:
        limiter_name = self._get_rate_limiter_name()
        limiter = get_rate_limiter(limiter_name)

        await limiter.acquire(blocking=True)

        client = await self._get_client()
        url = f"{self.BASE_URL}{endpoint}"

        default_headers = {}
        if headers:
            default_headers.update(headers)

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                if method == "GET":
                    response = await client.get(url, params=params, headers=default_headers)
                else:
                    response = await client.request(method, url, json=params, headers=default_headers)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", self.RETRY_DELAY * (2 ** attempt)))
                    logger.warning(f"Rate limited by {self.name}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code >= 400:
                    logger.error(f"Client error {response.status_code} for {url}")
                    return None

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                wait_time = self.RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Request timeout, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    return None
                last_error = e
                wait_time = self.RETRY_DELAY * (2 ** attempt)
                logger.warning(f"HTTP error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = e
                logger.error(f"Request failed: {e}")
                break

        if last_error:
            logger.error(f"All retries failed for {self.name}: {last_error}")
        return None

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
