# ai-coding-skills

AI Coding Skills —— 通用 AI 编程评测技能集合。

## 技能清单

| 技能 | 用途 | 输入参数 |
|---|---|---|
| [`eval-code-quality`](eval-code-quality/SKILL.md) | 对一个项目下的多个子项目做 12 维度代码质量打分，输出结构化 JSON 并聚合项目级评分 | 项目/子项目目录（`$ARGUMENTS`） |
| [`eval-prd-execution`](eval-prd-execution/SKILL.md) | 按内置 32 维度评价框架对 AI 生成项目做取证打分 | PRD 路径 + 项目目录（可选自述报告路径） |
| [`eval-runtime-cost`](eval-runtime-cost/SKILL.md) | 对运行成本 CSV 按 8 维权重打分，输出评分 CSV | 输入 CSV 路径（可选输出 CSV 路径） |

## 说明

- 每个技能一个独立目录，`SKILL.md` 为入口；`eval-prd-execution` 内置 32 维评价框架（`references/eval-dimensions.md`），`eval-runtime-cost` 内置打分脚本（`scripts/score_runtime_cost.py`）。
- 框架与脚本随技能分发；PRD、CSV 等数据作为运行参数传入，不依赖任何特定仓库。