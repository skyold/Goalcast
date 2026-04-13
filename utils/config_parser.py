import json
import re
import os
from typing import List, Dict, Any

def load_jsonc(file_path: str) -> Dict[str, Any]:
    """Load JSONC file by stripping comments before parsing."""
    if not os.path.exists(file_path):
        return {}
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Remove single-line comments (//) and multi-line comments (/* */)
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSONC in {file_path}: {e}")

def merge_markdown_files(directory: str, file_names: List[str]) -> str:
    """Merge content of specified markdown files in order."""
    merged_content = []
    
    for file_name in file_names:
        file_path = os.path.join(directory, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                merged_content.append(f.read().strip())
                
    return "\n\n".join(merged_content)