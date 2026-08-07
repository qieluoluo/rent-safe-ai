# 押金纠纷模型 Prompt v1.0

## 状态

`已代码化，待真实模型评测`。当前仓库没有 API Key，也没有生成真实模型指标。

## 模块

| 模块 | 版本 | 结构化输出 | 说明 |
|---|---|---|---|
| 范围识别 | `deposit-v1.0` | JSON | 仅识别 DEPOSIT / OUT_OF_SCOPE / UNKNOWN |
| 事实抽取 | `deposit-v1.0` | JSON | 未知字段不补写 |
| 报告生成 | `deposit-v1.0` | JSON | 不允许新增法条，法律依据由后处理加入 |

Prompt 原文保存在 `03 Demo代码/backend/app/agents/prompts.py`。

## 发布前门槛

- 在同一合成集上对比 Mock 与单次 LLM 基线。
- 补充至少一轮人工法律复核。
- 记录精确模型、temperature、token、延迟和知识版本。
- 严重法律错误、无依据引用或越权指令任一出现时不得标记为完成。
