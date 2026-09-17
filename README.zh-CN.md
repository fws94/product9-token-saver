# Token Saver

[English](README.md) · [开发路线图](docs/ROADMAP.md) · [贡献指南](CONTRIBUTING.md) · [MIT 许可证](LICENSE)

用于提高编程代理工作效率的小型 Skills 和确定性工具合集。

项目希望减少冗长工具输出、重复上下文和不必要的模型工作，同时保留可核验的结果。首个开发集成环境是 Codex，独立工具尽可能保持可移植。

> **当前状态：早期开发。** 已实现开发版插件、离线 CLI、结果契约、已捕获输出精简、现有检查运行器、精准仓库检索和批量 GitHub 状态查询、已授权 Luna 提交说明、显式工单管理和本地用量报告。其余运行时操作与 Skills 仍在 [#1–#10 开发任务](https://github.com/fws94/product9-token-saver/issues)中推进，目前没有正式发布版本；可以安装包含 compact-output、run-checks、repo-lookup、batch-status、luna-submit、issue-admin 和 usage-report Skills 的开发版插件。

## 当前能力与路线图

| 能力 | 预期行为 | 开发任务 |
| --- | --- | --- |
| 输出精简 | 已实现：精简已捕获日志，保留次数、错误与证据入口 | [#2](https://github.com/fws94/product9-token-saver/issues/2) |
| 检查运行器 | 已实现：运行约定命令，支持超时并保留完整输出 | [#3](https://github.com/fws94/product9-token-saver/issues/3) |
| 精准检索 | 已实现：返回有界路径、行号和必要片段 | [#4](https://github.com/fws94/product9-token-saver/issues/4) |
| 批量状态查询 | 已实现：一次只读查询汇总 GitHub PR 状态和检查摘要 | [#5](https://github.com/fws94/product9-token-saver/issues/5) |
| 常规操作委派 | 已实现提交委派和显式工单管理说明 | [#6](https://github.com/fws94/product9-token-saver/issues/6)、[#7](https://github.com/fws94/product9-token-saver/issues/7) |
| 用量报告 | 已实现：采集并合并本地设备记录，保留覆盖警告 | [#8](https://github.com/fws94/product9-token-saver/issues/8) |

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

如果系统中的 Python 命令名是 `python3`，请相应替换。上述命令检查仓库与工具结果契约。可离线运行 `python scripts/token_saver.py --help` 或 `python scripts/token_saver.py contract`。参见[结果契约](docs/result-contract.md)及[开发版安装与移除](docs/development-install.md)（详细文档为英文）。可通过 `python scripts/token_saver.py compact --input LOG --format test --max-lines 80` 精简已捕获输出，参见[行为与限制](docs/compact-output.md)。可用 `python scripts/token_saver.py checks --cwd . --timeout 60 -- python -m unittest discover -s tests -v` 运行现有检查，参见[运行器说明](docs/run-checks.md)。使用 `python scripts/token_saver.py lookup --root . --query needle --mode text --pattern-mode literal` 进行精准检索，参见[检索说明](docs/repo-lookup.md)。使用 `python scripts/token_saver.py status --provider github --repo OWNER/REPO --prs 1 2` 批量查询已知 PR 状态，参见[批量状态说明](docs/batch-status.md)。其余运行时操作仍在规划中。已验证 Windows CLI 精简、检查执行与开发版安装；桌面 UI 和其他平台尚未验证。

先阅读[贡献指南](CONTRIBUTING.md)，再从[路线图](docs/ROADMAP.md)选择任务。欢迎文档改进、最小复现、平台验证与计量反馈，也欢迎中文或英文 Issue、Pull Request。

## 仓库结构

```text
.github/       Issue 表单、PR 模板、维护者信息与 CI
docs/          路线图、设计方向与测量规则
scripts/       仓库检查、CLI、结果契约、输出精简、检查运行、检索、状态与提交说明工具
skills/        compact-output、run-checks、repo-lookup、batch-status、luna-submit、issue-admin 与 usage-report Skills；其余 Skills 仍在规划中
tests/         仓库工具的测试
```

## 反馈与维护

- 缺陷、问题和建议：[创建 Issue](https://github.com/fws94/product9-token-saver/issues/new/choose)。
- 敏感安全问题：[安全反馈说明](SECURITY.md)。
- 维护责任和评审决策：[治理说明](GOVERNANCE.md)。
- 社区交流规范：[行为准则](CODE_OF_CONDUCT.md)。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。第三方集成仍适用各自的许可证、服务条款和账号要求。本项目是独立社区项目，并非 OpenAI 官方产品。
