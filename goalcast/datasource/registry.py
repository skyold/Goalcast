from typing import Dict, List, Optional
from goalcast.datasource.base import DataSource, DataCapability
from goalcast.datasource.types import DataSourceType
from goalcast.utils.logger import logger


class DataRegistry:
    _instance: Optional['DataRegistry'] = None
    
    def __new__(cls) -> 'DataRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data_sources: Dict[DataSourceType, List[DataSource]] = {}
        return cls._instance
    
    def register(self, datasource: DataSource) -> None:
        dtype = datasource.data_type
        if dtype not in self._data_sources:
            self._data_sources[dtype] = []
        
        for existing in self._data_sources[dtype]:
            if existing.__class__.__name__ == datasource.__class__.__name__:
                logger.warning(f"DataSource {datasource.__class__.__name__} already registered")
                return
        
        self._data_sources[dtype].append(datasource)
        logger.info(f"Registered DataSource: {datasource}")
    
    def unregister(self, datasource: DataSource) -> None:
        dtype = datasource.data_type
        if dtype in self._data_sources:
            self._data_sources[dtype] = [
                ds for ds in self._data_sources[dtype] 
                if ds.__class__.__name__ != datasource.__class__.__name__
            ]
    
    def get(self, dtype: DataSourceType) -> Optional[DataSource]:
        sources = self._data_sources.get(dtype, [])
        return sources[0] if sources else None
    
    def get_all(self, dtype: DataSourceType) -> List[DataSource]:
        return self._data_sources.get(dtype, [])
    
    def capabilities(self) -> Dict[DataSourceType, DataCapability]:
        result = {}
        for dtype, sources in self._data_sources.items():
            if sources:
                result[dtype] = sources[0].capabilities()
        return result
    
    def list_all(self) -> Dict[DataSourceType, List[str]]:
        return {
            dtype: [ds.__class__.__name__ for ds in sources]
            for dtype, sources in self._data_sources.items()
        }
    
    def clear(self) -> None:
        self._data_sources.clear()
        logger.info("Registry cleared")


registry = DataRegistry()
