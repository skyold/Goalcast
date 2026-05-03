import json
from pathlib import Path
from typing import Any, Dict

def load_partial(filepath: str | Path, sections: list[str]) -> Dict[str, Any]:
    """从 JSON 文件中仅加载指定的顶级节点，以节省 LLM 上下文空间。"""
    path = Path(filepath)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if k in sections}

def merge_update(filepath: str | Path, updates: Dict[str, Any]) -> None:
    """将更新的内容深度合并到现有的 JSON 文件中。"""
    path = Path(filepath)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
        
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(data.get(k), dict):
            data[k].update(v)
        else:
            data[k] = v
            
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
