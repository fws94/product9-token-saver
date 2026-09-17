# Token Saver

[English](README.md) · [开发路线图](docs/ROADMAP.md) · [贡献指南](CONTRIBUTING.md) · [MIT 许可证](LICENSE)

用于提高编程代理工作效率的小型 Skills 和确定性工具合集。

项目希望减少冗长工具输出、重复上下文和不必要的模型工作，同时保留可核验的结果。首个开发集成环境是 Codex，独立工具尽可能保持可移植。

> **当前状态：早期开发。** 已实现开发版插件、离线 CLI、结果契约、已捕获输出精简和现有检查运行器。其余运行时操作与 Skills 仍在 [#1–#10 开发任务](https://github.com/fws94/product9-token-saver/issues)中推进，目前没有正式发布版本；可以安装包含 compact-output 和 run-checks Skills 的开发版插件。

## 当前能力与路线图

| 能力 | 预期行为 | 开发任务 |
| --- | --- | --- |
| 输出精简 | 已实现：精简已捕获日志，保留次数、错误与证据入口 | [#2](https://github.com/fws94/product9-token-saver/issues/2) |
| 检查运行器 | 已实现：运行约定命令，支持超时并保留完整输出 | [#3](https://github.com/fws94/product9-token-saver/issues/3) |
| 精准检索 | 返回相关路径、行号和必要片段 | [#4](https://github.com/fws94/product9-token-saver/issues/4) |
| 批量状态查询 | 减少重复查询，汇总 PR、CI 和工单状态 | [#5](https://github.com/fws94/product9-token-saver/issues/5) |
| 常规操作委派 | 将已明确授权的提交与工单更新交给适合的工作代理 | [#6](https://github.com/fws94/product9-token-saver/issues/6)、[#7](https://github.com/fws94/product9-token-saver/issues/7) |
| 用量报告 | 区分输入、缓存输入与输出，汇总设备本地报告 | [#8](https://github.com/fws94/product9-token-saver/issues/8) |

## 设计原则

- 明确、确定的工作优先使用工具；需要少量语言理解且值得交接的任务才使用轻量代理。
- 保留主任务的模型与推理设置，模型委派必须使用宿主实际支持的能力。
- 账号、目录和模型可配置，贡献者不需要使用维护者的个人环境。
- 精简后的输出保留完整证据入口，失败检查和结果不确定的写入不能被隐藏。
- 对整个任务计量，包括子代理、交接和重试。命令输出变短不能直接证明账号额度消耗下降。

## 现在可以怎样参与

准备 Git 与 Python 3.11 或更新版本即可运行仓库检查，不需要 API Key。

```bash
git clone https://github.com/fws94/product9-token-saver.git
cd product9-token-saver
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

如果系统中的 Python 命令名是 `python3`，请相应替换。上述命令检查仓库与工具结果契约。可离线运行 `python scripts/token_saver.py --help` 或 `python scripts/token_saver.py contract`。参见[结果契约](docs/result-contract.md)及[开发版安装与移除](docs/development-install.md)（详细文档为英文）。可通过 `python scripts/token_saver.py compact --input LOG --format test --max-lines 80` 精简已捕获输出，参见[行为与限制](docs/compact-output.md)。可用 `python scripts/token_saver.py checks --cwd . --timeout 60 -- python -m unittest discover -s tests -v` 运行现有检查，参见[运行器说明](docs/run-checks.md)。其余运行时操作仍在规划中。已验证 Windows CLI 精简、检查执行与开发版安装；桌面 UI 和其他平台尚未验证。

先阅读[贡献指南](CONTRIBUTING.md)，再从[路线图](docs/ROADMAP.md)选择任务。欢迎文档改进、最小复现、平台验证与计量反馈，也欢迎中文或英文 Issue、Pull Request。

## 仓库结构

```text
.github/       Issue 表单、PR 模板、维护者信息与 CI
docs/          路线图、设计方向与测量规则
scripts/       仓库检查、CLI、结果契约、输出精简与检查运行工具
skills/        compact-output 与 run-checks Skills；其余 Skills 仍在规划中
tests/         仓库工具的测试
```

## 反馈与维护

- 缺陷、问题和建议：[创建 Issue](https://github.com/fws94/product9-token-saver/issues/new/choose)。
- 敏感安全问题：[安全反馈说明](SECURITY.md)。
- 维护责任和评审决策：[治理说明](GOVERNANCE.md)。
- 社区交流规范：[行为准则](CODE_OF_CONDUCT.md)。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。第三方集成仍适用各自的许可证、服务条款和账号要求。本项目是独立社区项目，并非 OpenAI 官方产品。
