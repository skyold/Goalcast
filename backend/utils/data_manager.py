"""
数据文件管理工具
提供统一的数据文件存储路径管理
"""
import json
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

from config.settings import DATA_DIR


def get_data_file_path(filename: str, subdir: str = None) -> Path:
    """
    获取数据文件的完整路径
    
    Args:
        filename: 文件名（包含扩展名）
        subdir: 可选的子目录名称
        
    Returns:
        数据文件的完整路径
    """
    if subdir:
        dir_path = DATA_DIR / subdir
        dir_path.mkdir(exist_ok=True)
        return dir_path / filename
    return DATA_DIR / filename


def save_json_data(data: Dict[str, Any], filename: str, subdir: str = None) -> Path:
    """
    保存 JSON 数据到 data 目录
    
    Args:
        data: 要保存的字典数据
        filename: 文件名（不包含扩展名）
        subdir: 可选的子目录名称
        
    Returns:
        保存的文件路径
    """
    file_path = get_data_file_path(f"{filename}.json", subdir)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return file_path


def load_json_data(filename: str, subdir: str = None) -> Dict[str, Any]:
    """
    从 data 目录加载 JSON 数据
    
    Args:
        filename: 文件名（不包含扩展名）
        subdir: 可选的子目录名称
        
    Returns:
        加载的字典数据
    """
    file_path = get_data_file_path(f"{filename}.json", subdir)
    
    if not file_path.exists():
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_cache_path(filename: str) -> Path:
    """
    获取缓存文件路径（在 data/cache/ 目录下）
    
    Args:
        filename: 文件名
        
    Returns:
        缓存文件的完整路径
    """
    cache_dir = DATA_DIR / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / filename


def get_exports_path(filename: str) -> Path:
    """
    获取导出文件路径（在 data/exports/ 目录下）
    
    Args:
        filename: 文件名
        
    Returns:
        导出文件的完整路径
    """
    exports_dir = DATA_DIR / "exports"
    exports_dir.mkdir(exist_ok=True)
    return exports_dir / filename


def cleanup_old_files(days: int = 7) -> int:
    """
    清理 data 目录下超过指定天数的文件
    
    Args:
        days: 保留的天数，默认 7 天
        
    Returns:
        清理的文件数量
    """
    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    cleaned = 0
    
    for file_path in DATA_DIR.glob("*.json"):
        if file_path.stat().st_mtime < cutoff:
            file_path.unlink()
            cleaned += 1
    
    return cleaned
