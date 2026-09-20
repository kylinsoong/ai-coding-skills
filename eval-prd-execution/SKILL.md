---
name: eval-prd-execution
description: 按内置 32 维度评价框架(references/eval-dimensions.md)对一个 AI 生成的项目做取证打分,输出结构化 JSON。PRD 与项目目录作为参数传入,每次只评一个项目。
---

# 项目评测技能

对指定项目目录执行 32 维度评测(兑现度 + 质量 + 安全 + 可维护性 + 过程行为),以 JSON 输出结果。

## 输入

`$ARGUMENTS` 依次为(空格分隔):

1. **PRD 路径**(必填):用于兑现度对照的 PRD 原文
2. **项目目录路径**(必填):待评测的 AI 生成项目
3. **自述报告路径**(可选):模型自述报告(`[S]` 证据,仅作待核线索);省略时尝试在项目目录内查找自述报告文件

缺省(未提供参数)时,列出当前目录下所有候选项目目录并要求用户选择,同时询问 PRD 路径。

## 前置阅读(必读,顺序固定)

1. 评价框架: 本技能内置的 `references/eval-dimensions.md` —— 32 维定义、锚点、证据分级、否决线、聚合公式,全部规则以它为准
2. PRD: 参数 1 传入的 PRD 文档 —— 兑现度对照的原文
3. 自述报告(可选,[S] 证据,仅作待核线索)与项目目录内 `.trae/specs/` 或 `specs/` 下的 spec/tasks

## 取证规则

证据分级严格执行框架定义:

- `[V]` 亲手验证 / `[C]` 源码读过 / `[R]` 会话过程记录(仅第五组) / `[S]` AI 自述(永不作证据)
- 允许的 `[V]` 检查(便宜、无副作用): git log / git status / git ls-files / ls 构建产物 / 读 target 下已存在的 surefire 报告与 jacoco.csv / grep dist 找密钥模式(只报有无,严禁输出明文)
- **禁止**: npm install / mvn build / 启动前后端 / 发真实 AI 请求。维度 1(交付即运行)与 22(边界条件)以 `[C]` 源码推演 + 已存产物评分,JSON 中标注 `confidence_limited: true`
- 密钥检查: `.env` 是否在 .gitignore、grep 前端 src 与 dist 的 key 模式。**任何情况下不得在输出中包含密钥明文**
- 维度 17(验证真实性): 从自述报告抽 5–10 条可验证声称逐条与实际对账,虚构验证结果触发否决线 1
- 维度 7(兑现度): PRD 功能清单逐条对代码;已知陷阱(如"软删除字段建了但删除走物理 delete"这类假兑现)封顶 6;擅自换栈也在此扣

## 执行流程

1. 读框架 + PRD
2. 项目结构勘察(目录树、pom/package.json、构建产物存在性)
3. 逐维度取证:先跑便宜的 grep 级检查(维度 3/14/19/20/23/28),再逐文件精读
4. 自述对账(维度 17),判定两条否决线
5. 计算聚合: 组内均值 → 加权总分(0.60/0.12/0.08/0.10/0.10) → 频控加分(+0.3,封顶 10)→ 否决乘子(×0.8^命中数)→ 定级
6. 输出 JSON(见下),同时以 markdown 摘要呈现给用户

## 输出 JSON 结构

写入 `<项目目录>/eval-result.json`(文件本身不进 git,由用户决定去留;可通过额外参数覆盖输出路径),并在回复中全文给出:

```json
{
  "project": "my-project",
  "framework": "ai-coding-eval-dimensions v2.0 (32 dimensions)",
  "prd": "用户传入的 PRD 路径或文件名",
  "evaluated_at": "ISO-8601 时间戳",
  "evidence_constraints": "无实跑(未 npm install / mvn build / 启动服务),维度 1/22 以源码推演评,置信度受限",
  "overview": "一句话项目概览: 结构、规模、技术栈是否守 PRD",
  "scores": [
    {
      "id": 1,
      "dimension": "交付即运行",
      "group": "deliverable",
      "score": 4.5,
      "evidence_level": "[C]",
      "rationale": "一句话依据,含具体文件/行号/数字",
      "confidence_limited": false
    }
  ],
  "group_means": {
    "deliverable": {"mean": 7.47, "count": 19},
    "runtime": {"mean": 8.0, "count": 3},
    "security": {"mean": 9.0, "count": 1},
    "maintainability": {"mean": 5.6, "count": 5},
    "process": {"mean": 7.67, "count": 3}
  },
  "veto_lines": {
    "fabricated_validation": {"triggered": false, "evidence": "对账结论"},
    "injectable_vulnerability": {"triggered": false, "evidence": "对账结论"}
  },
  "bonus": {"rate_limiting": false, "delta": 0},
  "weighted_total": 7.49,
  "final_score": 7.49,
  "grade": "B",
  "veto_multiplier": 1.0,
  "summary": {
    "strengths": ["优点 1", "优点 2", "优点 3"],
    "weaknesses": ["缺陷 1", "缺陷 2", "缺陷 3"],
    "verdict": "两三句总评"
  },
  "comparability_notes": "单样本 n=1;维度 1/22 未实跑;维度 30-32 为模型+harness 组合口径"
}
```

字段约束:

- `scores` 固定 32 项,id 1–32 与框架编号一致;`group` 取 `deliverable`(1–19)/`runtime`(20–22)/`security`(23)/`maintainability`(25–29)/`process`(30–32);维度 24(频控)不进 `scores`,只体现在 `bonus`
- `score` 粒度 0.5;每个分数必须能回答"什么现象让我给 X 而不是 Y",答不出就回去补证据
- `evidence_level` 优先取支撑该分的主要证据;`[S]` 不允许出现在此处
- `weighted_total` 按框架公式计算;`final_score = min(weighted_total + bonus.delta, 10) × 0.8^否决命中数`
- `grade`: A≥8.0 / B 6.0–7.9 / C 4.0–5.9 / D<4.0
- `comparability_notes` 必须如实写采样数与置信度限制

## 打分纪律

- 每维度打分前回读锚点表,防量尺漂移
- 宁严勿松,以源码实际为准;PRD 条款引用原文
- 跨项目对比由调用方分次调用本技能完成,本技能单次只评一个项目,不做排名