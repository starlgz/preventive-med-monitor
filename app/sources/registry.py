import importlib
import pkgutil
import inspect
from typing import Dict, List, Type
from app.sources.base import BaseSource, RawAnnouncementItem, RawAnnouncementDetail
from app.sources.provinces_pool import get_all_province_sources
from app.core.logger import logger
import app.sources

class DynamicProvinceSource(BaseSource):
    """
    通用省份官方招考适配器 (用于全国省池动态注册)
    """
    def __init__(self, code: str, name: str, province: str, base_url: str, category: str):
        super().__init__()
        self.source_id = code
        self.name = name
        self.province = province
        self.base_url = base_url
        self.category = category

    async def fetch_announcements(self, max_pages: int = 1) -> List[RawAnnouncementItem]:
        return []

    async def fetch_detail(self, announcement_url: str) -> RawAnnouncementDetail:
        return None

class SourceRegistry:
    """
    数据源插件注册中心 (动态热插拔与发现机制)
    """
    _plugins: Dict[str, BaseSource] = {}
    SOURCE_REGISTRY: Dict[str, BaseSource] = _plugins


    @classmethod
    def discover_and_register(cls) -> Dict[str, BaseSource]:
        """
        自动扫描 app/sources/ 目录下所有模块并实例化继承了 BaseSource 的插件，同时注册全国省池源
        """
        cls._plugins.clear()
        package = app.sources
        
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            if module_name in ["base", "registry", "provinces_pool"]:
                continue
            
            try:
                full_module_name = f"app.sources.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # 遍历模块中的所有类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseSource) and obj is not BaseSource and obj is not DynamicProvinceSource:
                        instance = obj()
                        if instance.source_id in cls._plugins:
                            logger.warning(f"Duplicate source_id detected: {instance.source_id}, overwriting.")
                        cls._plugins[instance.source_id] = instance
                        logger.info(f"Registered source plugin: [{instance.source_id}] {instance.name} (category={instance.category}, province={instance.province})")
            except Exception as e:
                logger.error(f"Failed to load source plugin from module {module_name}: {e}")

        # 注册全国省池适配源（专属已实现插件优先）
        for p in get_all_province_sources():
            if p["code"] not in cls._plugins and f"{p['code']}_custom" not in cls._plugins:
                dyn_source = DynamicProvinceSource(
                    code=p["code"],
                    name=p["name"],
                    province=p["province"],
                    base_url=p["url"],
                    category=p["category"]
                )
                cls._plugins[p["code"]] = dyn_source

        logger.info(f"Total source plugins registered: {len(cls._plugins)}")
        return cls._plugins

    @classmethod
    def get(cls, source_id: str) -> BaseSource:
        return cls._plugins.get(source_id)

    @classmethod
    def get_all(cls) -> List[BaseSource]:
        return list(cls._plugins.values())

    @classmethod
    def get_active(cls) -> List[BaseSource]:
        return [p for p in cls._plugins.values() if p.enabled]

# 辅助函数兼容接口
def get_source_by_key(key: str) -> BaseSource:
    if not SourceRegistry._plugins:
        SourceRegistry.discover_and_register()
    return SourceRegistry.get(key)

def list_all_sources() -> Dict[str, BaseSource]:
    if not SourceRegistry._plugins:
        SourceRegistry.discover_and_register()
    return SourceRegistry._plugins
