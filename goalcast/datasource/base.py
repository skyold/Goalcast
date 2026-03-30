from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta
from goalcast.datasource.types import DataSourceType
from goalcast.provider.base import BaseProvider
from goalcast.utils.logger import logger

T = TypeVar('T')


@dataclass
class DataCapability:
    type: DataSourceType
    name: str
    description: str
    providers: List[str]
    params: Dict[str, str]
    update_freq: float
    historical: bool
    realtime: bool


class DataSource(ABC, Generic[T]):
    def __init__(self, providers: List[BaseProvider] = None):
        self._providers: List[BaseProvider] = providers or []
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: float = 30.0

    @property
    @abstractmethod
    def data_type(self) -> DataSourceType:
        pass

    @abstractmethod
    def capabilities(self) -> DataCapability:
        pass

    @abstractmethod
    async def fetch(self, **params) -> Optional[T]:
        pass

    @abstractmethod
    def parse(self, raw_data: Dict[str, Any]) -> T:
        pass

    async def is_available(self) -> bool:
        for provider in self._providers:
            if await provider.is_available():
                return True
        return False

    def _cache_key(self, **params) -> str:
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        return ":".join(f"{k}={v}" for k, v in sorted_params if v is not None)

    def _get_from_cache(self, key: str) -> Optional[T]:
        if key in self._cache:
            cached = self._cache[key]
            if datetime.now() - cached["time"] < timedelta(seconds=self._cache_ttl):
                logger.debug(f"Cache hit for {key}")
                return cached["data"]
        return None

    def _set_cache(self, key: str, data: T) -> None:
        self._cache[key] = {
            "data": data,
            "time": datetime.now(),
        }
        logger.debug(f"Cache set for {key}")

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.debug("Cache cleared")

    async def _try_providers(self, method_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        last_error = None
        for provider in self._providers:
            try:
                if not await provider.is_available():
                    continue
                
                method = getattr(provider, method_name, None)
                if method is None:
                    continue
                
                result = await method(**kwargs)
                if result is not None:
                    logger.debug(f"Provider {provider.name} succeeded for {method_name}")
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue
        
        if last_error:
            logger.error(f"All providers failed for {method_name}: {last_error}")
        return None

    def add_provider(self, provider: BaseProvider) -> None:
        if provider not in self._providers:
            self._providers.append(provider)

    def remove_provider(self, provider_name: str) -> None:
        self._providers = [p for p in self._providers if p.name != provider_name]

    def __repr__(self) -> str:
        provider_names = [p.name for p in self._providers]
        return f"<{self.__class__.__name__} type={self.data_type.value} providers={provider_names}>"
