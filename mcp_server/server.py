"""
server.py — Goalcast MCP Server 入口层

本文件仅负责：
1. 初始化 FastMCP 实例
2. 初始化共享的 Sportmonks service
3. 注册按数据源/能力拆分的 MCP 工具模块

工具模块划分：
- `mcp_server/tools/sportmonks.py`
- `mcp_server/tools/footystats.py`
- `mcp_server/tools/quant.py`

内部 provider 包装、helper 与非 MCP 逻辑位于 `internal.py`。
"""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

try:
    from internal import get_sportmonks
except ImportError:
    from mcp_server.internal import get_sportmonks

from datasource.sportmonks.service import SportmonksDataService
from mcp_server.tools.footystats import register_goalcast_footystats_tools
from mcp_server.tools.sportmonks import register_goalcast_sportmonks_tools
from mcp_server.tools.quant import register_goalcast_quant_tools
from mcp_server.tools.evaluation import register_goalcast_evaluation_tools


mcp = FastMCP(
    "Goalcast Data Providers",
    host=os.environ.get("FASTMCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
)

_sportmonks_data_service: Optional[SportmonksDataService] = None


def get_sportmonks_data_service() -> SportmonksDataService:
    """懒加载 SportmonksDataService 实例。"""
    global _sportmonks_data_service
    if _sportmonks_data_service is None:
        _sportmonks_data_service = SportmonksDataService(
            provider=get_sportmonks(),
        )
    return _sportmonks_data_service


register_goalcast_sportmonks_tools(mcp, service_factory=get_sportmonks_data_service)
register_goalcast_footystats_tools(mcp)
register_goalcast_quant_tools(mcp)
register_goalcast_evaluation_tools(mcp)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run()
