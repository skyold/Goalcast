import pytest
from utils.config_parser import load_jsonc, merge_markdown_files
import os

def test_load_jsonc(tmp_path):
    jsonc_content = """
    {
        // This is a comment
        "builtin": {"include": ["read", "write"]}
    }
    """
    file_path = tmp_path / "test.jsonc"
    file_path.write_text(jsonc_content)
    
    result = load_jsonc(str(file_path))
    assert "builtin" in result
    assert "include" in result["builtin"]
    assert "read" in result["builtin"]["include"]

def test_merge_markdown_files(tmp_path):
    (tmp_path / "IDENTITY.md").write_text("# Identity\nI am a bot.")
    (tmp_path / "SOUL.md").write_text("# Soul\nI am helpful.")
    
    # Missing file should be ignored
    result = merge_markdown_files(str(tmp_path), ["IDENTITY.md", "MISSING.md", "SOUL.md"])
    assert "# Identity" in result
    assert "I am a bot." in result
    assert "# Soul" in result
    assert "I am helpful." in result