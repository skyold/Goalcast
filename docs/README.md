# Docs

Goalcast 项目文档目录。按主题分类组织。

---

## Architecture & Design

项目架构、设计决策和技术规范。

- [Code Wiki](Code_Wiki.md) - 项目整体架构、模块职责、关键类说明
- [Goalcast Skill](GOALCAST_SKILL.md) - 标准分析工作流参考

## Setup & Config

配置和设置相关文档。

- [Data Directory Setup](DATA_DIRECTORY_SETUP.md) - data 目录结构和使用说明
- [MCP Config Guide](MCP_CONFIG_GUIDE.md) - MCP 服务器配置详细说明（相对路径 vs 环境变量 vs Docker）
- [MCP Migration Guide](MCP_MIGRATION_GUIDE.md) - MCP 服务器迁移指南（本地 -> Docker -> 远程服务器）

## Deploy

部署和运维相关文档。

- [Quick Start](DEPLOY_QUICK_START.md) - 服务器部署 MCP 快速指南
- [Server Deployment](SERVER_DEPLOYMENT.md) - Docker 部署完整指南（含运维、安全、性能优化）
- [Deploy Usage](DEPLOY_USAGE.md) - `goalcast-deploy.sh` 统一部署工具使用说明
- [Docker Build Troubleshooting](DOCKER_BUILD_TROUBLESHOOTING.md) - Docker 构建故障排查（版本兼容性）
- [Docker Network Timeout](DOCKER_NETWORK_TIMEOUT.md) - 中国大陆 pip 镜像源配置

## Providers

数据源 Provider 使用和测试文档。

### Sportmonks
- [Sportmonks Usage](SPORTMONKS_USAGE.md) - API v3 深度使用指南（赔率、xG、统计、批量采集）
- [Sportmonks Test Report](SPORTMONKS_TEST_REPORT.md) - 免费计划端点测试报告（6/22 可用）
- [Sportmonks Data Investigation](SPORTMONKS_DATA_AVAILABILITY_INVESTIGATION_2026-04-14_2026-04-18.md) - 数据可用性调查报告（P0: odds/xG 问题）

### Understat
- [Understat Integration](UNDERSTAT_INTEGRATION.md) - understatapi 库集成说明和使用示例

## Superpowers

设计规划文档（由 AI 辅助生成）。

### Plans (实施计划)
- [2026-04-07 Goalcast Skill Pipeline](superpowers/plans/2026-04-07-goalcast-skill-pipeline.md)
- [2026-04-12 Goalcast Refactor](superpowers/plans/2026-04-12-goalcast-refactor.md)
- [2026-04-13 Directory Agent System](superpowers/plans/2026-04-13-directory-agent-system-plan.md)
- [2026-04-13 Multi-Agent Framework](superpowers/plans/2026-04-13-multi-agent-framework-plan.md)
- [2026-04-14 Provider-Specific Data Architecture](superpowers/plans/2026-04-14-provider-specific-data-architecture.md)
- [2026-04-15 Sportmonks Data Layer](superpowers/plans/2026-04-15-goalcast-sportmonks-data-layer.md)
- [2026-04-16 V40 Smart Routing](superpowers/plans/2026-04-16-goalcast-v40-smart-routing-plan.md)

### Specs (设计规格)
- [2026-04-07 Skill Pipeline Design](superpowers/specs/2026-04-07-goalcast-skill-pipeline-design.md)
- [2026-04-12 Refactor Design](superpowers/specs/2026-04-12-goalcast-refactor-design.md)
- [2026-04-13 Directory Agent System Design](superpowers/specs/2026-04-13-directory-agent-system-design.md)
- [2026-04-13 Multi-Agent Framework Design](superpowers/specs/2026-04-13-multi-agent-framework-design.md)
- [2026-04-14 Provider-Specific Data Architecture Design](superpowers/specs/2026-04-14-provider-specific-data-architecture-design.md)
- [2026-04-15 Sportmonks Data Layer Design](superpowers/specs/2026-04-15-goalcast-sportmonks-data-layer-design.md)
- [2026-04-16 Sportmonks MCP Agent Readonly Design](superpowers/specs/2026-04-16-sportmonks-mcp-agent-readonly-design.md)
- [2026-04-16 Sportmonks Refactor Design](superpowers/specs/2026-04-16-sportmonks-refactor-design.md)
- [2026-04-16 V40 Smart Routing Design](superpowers/specs/2026-04-16-goalcast-v40-smart-routing-design.md)

### Fixtures
- [FootyStats Field Map](superpowers/fixtures/footystats-field-map.md)
- [Test Match Validation](superpowers/fixtures/test-match-validation.md)

## Changelog / Archive

一次性工作记录和历史归档。

- [Dependencies Cleanup](DEPENDENCIES_CLEANUP.md) - 依赖模块精简记录（13 -> 3 核心依赖）
- [Script Merge Explanation](SCRIPT_MERGE_EXPLANATION.md) - 部署脚本合并记录
- [Skills Refactoring Summary](SKILLS_REFACTORING_SUMMARY.md) - Skills 重构记录
- [Understat Development](UNDERSTAT_DEVELOPMENT.md) - Understat Provider 开发日志
- [Understat Implementation Summary](UNDERSTAT_IMPLEMENTATION_SUMMARY.md) - Understat 实现总结

## Review

- [Review Report](REVIEW_REPORT.md) - 2026-05-01 文档与代码 Review 报告

---

## Other Project Docs

项目中其他位置的文档：

- [Project README](../README.md) - 项目主文档
- [Data README](../data/README.md) - data 目录使用指南
- [FootyStats Provider](../provider/footystats/README.md) - FootyStats API 使用
- [Sportmonks Provider](../datasource/sportmonks/README.md) - Sportmonks 数据源
- [MCP Server](../mcp_server/README.md) - MCP 服务器说明
- [Skills](../skills/README.md) - Skills 目录总览
- [Debug](../debug/README.md) - 调试工具
