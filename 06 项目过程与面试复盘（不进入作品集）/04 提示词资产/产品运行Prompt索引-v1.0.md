# 产品运行 Prompt 索引 v1.0

> **用途：** 索引租安 AI 对用户案件执行分析时使用的 Prompt / 规则版本  
> **说明：** 产品运行 Prompt 保存在技术设计与代码中，本文件为 06 目录内的统一索引

---

## 当前版本

| 名称 | 版本 | 类型 | 保存位置 | 状态 |
|---|---|---|---|---|
| Mock 规则基线 | mock-v1.2 | 规则 Provider | `03 Demo代码/backend/app/agents/mock_provider.py` | **当前演示基线** |
| Mock 规则基线（旧） | mock-v1.1 | 规则 Provider | `04 AI效果验证/Prompt版本记录/mock-v1.1.md` | 已 supersede |
| 真实模型 Prompt | deposit-v1.0 | LLM Prompt | `03 Demo代码/backend/app/agents/prompts.py` | 已编码，待真实模型评测 |
| Prompt 设计文档 | v1.0 | 设计规格 | `02 技术设计/Prompt设计.md` | 9 类 Prompt 完整设计 |

---

## 版本变更记录

| 版本 | 日期 | 变化 | 验证 |
|---|---|---|---|
| mock-v1.1 | 2026-08-06 | 首版规则基线 | 23 条合成集，6 Case 失败 |
| mock-v1.2 | 2026-08-06 | 修复 6 个 Bad Case | 23/23 全通过 |
| deposit-v1.0 | 2026-08-06 | OpenAI-compatible Prompt 编码 | 尚无真实模型评测结果 |

---

## 关联评测

- 评测脚本：`04 AI效果验证/evaluate_mock.py`
- 测试集：`04 AI效果验证/测试案例/deposit-v1-synthetic.jsonl`
- 最新结果：`04 AI效果验证/评测结果/mock-baseline-v1.2.json`
- Bad Case：`04 AI效果验证/Bad Case优化记录/2026-08-06-mock-v1.1-首次回归.md`

---

## 使用规则

- Mock 与真实模型结果必须分开保存，不得混写。
- 每次 Prompt/规则变更必须在开发日志中记录，并执行全量回归。
- 对外表述必须标注「演示模式」或「规则基线」，不得冒充真实大模型能力。
