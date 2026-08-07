# 租安 AI —— AI Agent 流程设计文档

> **文档类型：** 技术设计文档 - AI Agent 工作流详细设计
> **前置文档：**
> - [产品需求分析.md](file:///e:/_产品/法律RAG/租安%20AI——租房纠纷智能分析与证据管理平台/产品文档/产品需求分析.md)
> - [PRD核心功能详细设计.md](file:///e:/_产品/法律RAG/租安%20AI——租房纠纷智能分析与证据管理平台/产品文档/PRD核心功能详细设计.md)
> - [数据库设计.md](file:///e:/_产品/法律RAG/租安%20AI——租房纠纷智能分析与证据管理平台/技术设计/数据库设计.md)
> **版本：** V1.0

> **V1 演示模式实现说明（2026-08-07）：** 当前代码实现为 **6 步同步 Mock 工作流**（意图→抽取→完整度→检索→风险→报告），Provider 为 `mock-v1.2` 规则基线。本文档描述的 7 节点架构（含独立追问循环和幻觉校验）是**目标设计**；V1 中追问问题由完整度节点直接输出，幻觉校验由报告 disclaimer 替代。详见 `03 Demo代码/backend/app/agents/orchestrator.py`。

---

## 目录

```
一、Agent 架构总览
    1.1 为什么用多节点串联而非单次 LLM 调用
    1.2 Agent 整体架构图
    1.3 节点职责划分
    1.4 节点间通信协议

二、主工作流：AI 纠纷智能分析（7 个节点串联）
    2.0 主工作流总览图
    2.1 节点1：意图识别（LLM）
    2.2 节点2：信息抽取（LLM）
    2.3 节点3：信息完整度判断（规则 + LLM）
    2.4 节点4：追问生成（LLM）
    2.5 节点5：RAG 知识检索（Embedding + FAISS）
    2.6 节点6：分析报告生成（LLM + Prompt）
    2.7 节点7：幻觉校验（规则校验）

三、子工作流：AI 证据智能管理
    3.1 子工作流总览图
    3.2 节点A：文件类型判断
    3.3 节点B：OCR 内容提取
    3.4 节点C：关键信息提取（LLM）
    3.5 节点D：证据评分（LLM + 规则）
    3.6 节点E：证据目录生成

四、子工作流：AI 行动指南生成
    4.1 子工作流总览图
    4.2 节点F：读取案件上下文
    4.3 节点G：阶段判断（规则）
    4.4 节点H：RAG 检索
    4.5 节点I：行动方案生成（LLM）

五、节点间数据流转（JSON 示例）
    5.1 主工作流完整数据流
    5.2 证据管理子工作流数据流
    5.3 行动指南子工作流数据流

六、设计决策说明表（面试可讲）

七、技术实现方案
    7.1 技术栈选型
    7.2 各节点技术实现
    7.3 工程目录结构建议
    7.4 异常与重试机制
    7.5 可观测性与效果评估
```

---

## 一、Agent 架构总览

### 1.1 为什么用多节点串联而非单次 LLM 调用

最朴素的实现是：把用户描述一股脑丢给 LLM，让它直接输出分析报告。这种方案在 Demo 阶段能跑通，但产品化会遇到 4 个致命问题：

| 问题 | 单次调用的表现 | 多节点串联的解决方式 |
|------|---------------|---------------------|
| 幻觉严重 | LLM 凭记忆引用法条，常出现"民法典第 888 条"这种不存在的条文 | 节点5 RAG 先检索真实法条，节点6 LLM 只基于检索结果整合，节点7 再校验一次 |
| 信息缺失无感知 | 用户说一句"房东不退押金"，LLM 直接给出建议，但漏掉了金额、合同状态等关键信息 | 节点3 完整度判断 + 节点4 追问循环，强制补齐信息到 80% 才进入报告生成 |
| 无法针对单步优化 | 想优化"押金纠纷识别准确率"，只能改整段 Prompt，牵一发动全身 | 每个节点独立 Prompt，独立评估指标，独立迭代 |
| 异常不可恢复 | LLM 输出格式错误，整条链路失败，用户什么也拿不到 | 节点级失败可重试、可降级，单节点失败不影响其他节点 |
| 成本不可控 | 每次都跑完整 Prompt，token 消耗大 | 简单意图在节点1 就能判定，可按需跳过节点 |

> **小白理解：** 把"做一份法律分析报告"拆成"分类→抽取→检查→检索→生成→校验"6 个步骤，就像律师办案：先听你说什么类型的案子，再问清楚细节，发现信息不够就追问，然后查法条，最后写报告，写完还要核对法条引用对不对。每一步都可独立检查、独立改进。

### 1.2 Agent 整体架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                        租安 AI Agent 架构                              │
└──────────────────────────────────────────────────────────────────────┘

  用户层        ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  (Frontend)    │  案件创建页  │   │  证据上传页  │   │  行动指南页  │
                └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
                       │                 │                 │
                       ▼                 ▼                 ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                       Agent 编排层 (Orchestrator)                  │
  │                                                                    │
  │   ┌──────────────────────────────────────────────────────────┐    │
  │   │   主工作流：AI 纠纷智能分析 (7 节点串联 + 追问循环)         │    │
  │   │   1→2→3→4(循环回2)→5→6→7                                  │    │
  │   └──────────────────────────────────────────────────────────┘    │
  │                                                                    │
  │   ┌──────────────────────────────────────────────────────────┐    │
  │   │   子工作流A：证据智能管理 (5 节点：A→B→C→D→E)              │    │
  │   └──────────────────────────────────────────────────────────┘    │
  │                                                                    │
  │   ┌──────────────────────────────────────────────────────────┐    │
  │   │   子工作流B：行动指南生成 (4 节点：F→G→H→I)                │    │
  │   └──────────────────────────────────────────────────────────┘    │
  └──────────────────────────────────────────────────────────────────┘
                       │                 │                 │
                       ▼                 ▼                 ▼
  能力层          ┌──────────┐    ┌──────────┐    ┌──────────┐
  (Capability)    │  LLM 调用 │    │ RAG 检索 │    │  OCR 解析 │
                  │ DeepSeek │    │  FAISS   │    │ Tesseract│
                  └──────────┘    └──────────┘    └──────────┘
                       │                 │                 │
                       ▼                 ▼                 ▼
  数据层          ┌──────────┐    ┌──────────┐    ┌──────────┐
  (Data)          │ 业务数据库│    │ 向量库    │    │ 文件存储  │
                  │  MySQL   │    │  FAISS   │    │  Local/  │
                  │ ai_task  │    │  index   │    │  OSS     │
                  └──────────┘    └──────────┘    └──────────┘
```

### 1.3 节点职责划分

| 节点编号 | 节点名称 | 实现方式 | 输入来源 | 输出去向 | 可独立失败 |
|---------|---------|---------|---------|---------|-----------|
| 1 | 意图识别 | LLM | 用户描述 | 节点2 | 是（可降级为"通用咨询"） |
| 2 | 信息抽取 | LLM | 节点1 + 用户描述 | 节点3 | 是（输出空 JSON 兜底） |
| 3 | 完整度判断 | 规则 + LLM | 节点2 输出 | 节点4 或 节点5 | 是（默认 60% 完整度） |
| 4 | 追问生成 | LLM | 节点3 缺失字段 | 用户（前端） | 是（用模板兜底） |
| 5 | RAG 检索 | Embedding + FAISS | 节点2 + 节点1 | 节点6 | 是（返回空数组兜底） |
| 6 | 报告生成 | LLM + Prompt | 节点2 + 3 + 5 | 节点7 | 否（核心节点，失败重试） |
| 7 | 幻觉校验 | 规则校验 | 节点6 输出 | 用户（前端） | 是（标记警告即可） |

### 1.4 节点间通信协议

所有节点之间通过 **统一的 JSON 结构** 通信，这个结构称为 **CaseContext（案件上下文）**，每个节点读取自己需要的字段，写回自己产出的字段，逐步累积信息。

```json
{
  "case_id": 1001,
  "user_id": 2001,
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
  "case_type": null,
  "intent": null,
  "extracted_info": null,
  "completeness": null,
  "missing_fields": null,
  "follow_up_question": null,
  "rag_results": null,
  "report": null,
  "hallucination_check": null,
  "ai_tasks": [],
  "metadata": {
    "version": "1.0",
    "created_at": "2026-08-05T10:00:00Z",
    "updated_at": "2026-08-05T10:00:30Z"
  }
}
```

> **小白理解：** 想象 CaseContext 是一个"案件档案袋"，每经过一个节点，就往袋子里塞一张新表格。下个节点只看袋子里自己需要的表格，干完活再塞回新的表格，不需要知道前面是谁干的活。

---

## 二、主工作流：AI 纠纷智能分析（7 个节点串联）

### 2.0 主工作流总览图

```
                       用户输入纠纷描述
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点1：意图识别 (LLM)             │
              │  输出：case_type + confidence     │
              │  置信度<0.6 → 重试 / 转人工        │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点2：信息抽取 (LLM)             │
              │  输出：extracted_info (结构化)    │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点3：信息完整度判断 (规则+LLM)  │
              │  输出：completeness + missing     │
              └───────────────┬───────────────────┘
                              │
                       完整度≥80%?
                       │        │
                    否 │        │ 是
              ┌────────▼──┐     │
              │ 节点4：    │     │
              │ 追问生成   │     │
              │ (LLM)      │     │
              │           │     │
              │ 输出追问   │     │
              │ → 用户补充 │     │
              │ → 回到节点2│     │
              └────────┬──┘     │
                       │        │
                       └────┬───┘
                            ▼
              ┌───────────────────────────────────┐
              │  节点5：RAG 知识检索              │
              │  (Embedding + FAISS)              │
              │  输出：rag_results (Top-K 法条)   │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点6：分析报告生成 (LLM+Prompt) │
              │  输出：report (5 部分结构化报告)  │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点7：幻觉校验 (规则校验)        │
              │  输出：hallucination_check        │
              │  有幻觉 → 标记警告 + 删除虚构法条 │
              └───────────────┬───────────────────┘
                              │
                              ▼
                       输出最终报告给用户
```

### 2.1 节点1：意图识别（LLM）

#### 节点定位
判断用户描述属于哪一类租房纠纷，是后续所有节点分支的依据。

#### 输入

```json
{
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。"
}
```

#### 处理逻辑

1. 把用户描述 + 系统提示词组装成 Prompt
2. 调用 LLM，要求输出 JSON 格式
3. 解析 JSON，取出 case_type 和 confidence
4. 若 confidence < 0.6，重试一次（在 Prompt 中追加"如果无法判断请输出 UNKNOWN"）
5. 若仍 < 0.6，降级为 `case_type=UNKNOWN`，前端引导用户手动选择

#### Prompt 示例

```
你是一名租房纠纷分类助手。请根据用户描述判断纠纷类型。

【支持的纠纷类型】
- DEPOSIT：押金纠纷（房东不退/少退押金）
- RENT_CANCEL：提前退租（提前解约、违约金争议）
- REPAIR：维修责任（房屋设施损坏、维修义务归属）
- CONTRACT：合同风险（合同条款争议、合同无效）
- UNKNOWN：无法判断

【用户描述】
{description}

【输出格式（必须严格输出 JSON，不要任何额外说明）】
{
  "case_type": "DEPOSIT",
  "confidence": 0.93,
  "reason": "用户明确提到押金不退，属于押金纠纷"
}
```

#### 输出

```json
{
  "intent": {
    "case_type": "DEPOSIT",
    "confidence": 0.93,
    "reason": "用户明确提到押金不退，属于押金纠纷"
  }
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| LLM 返回非 JSON | 用正则提取 JSON 片段；提取失败则重试一次 |
| 置信度 < 0.6 | 重试一次；仍 < 0.6 则降级为 UNKNOWN |
| LLM 超时（>10s） | 重试一次；仍失败则降级为 UNKNOWN |
| description 为空或长度 < 5 | 直接返回"描述过短"提示，不调用 LLM |
| description > 2000 字 | 截取前 2000 字送入 LLM |

#### 技术实现

| 项目 | 选型 |
|------|------|
| LLM | DeepSeek API（`deepseek-chat`） |
| 调用方式 | LangChain `ChatOpenAI` 包装，或直接 `openai` SDK |
| JSON 解析 | LangChain `StructuredOutputParser` 或正则兜底 |
| 重试 | `tenacity` 库，最多 2 次，指数退避 |
| 日志 | 每次调用记录到 `ai_task` 表，task_type=INTENT |

---

### 2.2 节点2：信息抽取（LLM）

#### 节点定位
从用户非结构化描述中，抽取出后续分析需要的结构化字段。这是整个工作流的"信息地基"。

#### 输入

```json
{
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
  "case_type": "DEPOSIT"
}
```

#### 处理逻辑

1. 根据 case_type 加载对应的"抽取字段清单"
   - DEPOSIT 押金纠纷 → 抽取：角色、押金金额、扣款原因、合同状态、房东态度、是否沟通过
   - REPAIR 维修纠纷 → 抽取：角色、损坏设施、维修责任方、是否报修、维修费用、合同维修条款
   - 其他类型同理
2. 把字段清单 + 用户描述组装 Prompt
3. 调用 LLM，要求严格 JSON 输出
4. 若用户在追问循环中补充了新信息，本次抽取要合并上一轮的抽取结果（增量更新）

#### Prompt 示例（DEPOSIT 类型）

```
你是一名租房纠纷信息抽取助手。请从用户描述中抽取以下字段。

【纠纷类型】押金纠纷

【需要抽取的字段】
- role：用户角色（tenant/landlord/unknown）
- deposit_amount：押金金额（数字，单位元，无则 null）
- deduction_reason：房东扣款原因（字符串，无则 null）
- contract_status：合同状态（active/expired/terminated/unknown）
- landlord_attitude：房东态度（cooperative/refused/unknown）
- has_communication：是否沟通过（true/false/unknown）
- communication_record：沟通情况描述（字符串）

【用户描述】
{description}

【上一轮已抽取的信息（如有追问补充）】
{previous_extracted_info}

【输出格式（严格 JSON）】
{
  "role": "tenant",
  "deposit_amount": 3000,
  "deduction_reason": "墙面损坏",
  "contract_status": "expired",
  "landlord_attitude": "refused",
  "has_communication": true,
  "communication_record": "用户提到房东直接拒绝退还"
}

【规则】
1. 字段值无法从描述中判断时，填 null，不要编造
2. 金额必须是数字，不要带"元"字
3. 不要输出任何额外说明
```

#### 输出

```json
{
  "extracted_info": {
    "role": "tenant",
    "deposit_amount": 3000,
    "deduction_reason": "墙面损坏",
    "contract_status": "expired",
    "landlord_attitude": "refused",
    "has_communication": true,
    "communication_record": "用户提到房东直接拒绝退还"
  }
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| LLM 编造字段值 | Prompt 中明确"无法判断填 null"；输出后用规则校验 null 字段比例，>50% 则降级 |
| 字段类型错误（如金额是字符串） | 后处理时做类型转换，转换失败置 null |
| LLM 返回非 JSON | 同节点1 处理方式 |
| 用户描述信息太少 | 输出全 null 的结构，交给节点3 判断完整度，触发追问 |

#### 技术实现

| 项目 | 选型 |
|------|------|
| LLM | DeepSeek API |
| 字段清单配置 | Python 字典 / YAML 文件，按 case_type 索引 |
| JSON 校验 | Pydantic Model 定义 `ExtractedInfoSchema`，自动校验类型 |
| 增量合并 | 字段级 merge，新值覆盖旧值，null 不覆盖 |

---

### 2.3 节点3：信息完整度判断（规则 + LLM）

#### 节点定位
对比"标准要素清单"和节点2 抽取出的字段，判断信息是否够生成准确报告。**这是决定是否触发追问的关键节点。**

#### 输入

```json
{
  "case_type": "DEPOSIT",
  "extracted_info": {
    "role": "tenant",
    "deposit_amount": 3000,
    "deduction_reason": "墙面损坏",
    "contract_status": "expired",
    "landlord_attitude": "refused",
    "has_communication": true,
    "communication_record": "用户提到房东直接拒绝退还"
  }
}
```

#### 处理逻辑

1. 根据 case_type 加载"标准要素清单"
2. **规则层：** 遍历清单，逐项检查 extracted_info 中对应字段是否为 null
3. 计算完整度 = 已填字段数 / 总字段数
4. **LLM 层（可选）：** 若完整度处于 60%-80% 灰度区间，调用 LLM 判断"这些缺失字段是否影响分析结论"，避免机械追问
5. 完整度 ≥ 80% → 进入节点5；< 80% → 进入节点4

#### 标准要素清单（DEPOSIT 押金纠纷）

```python
REQUIRED_FIELDS = {
    "DEPOSIT": [
        {"field": "role", "name": "用户角色", "required": True, "weight": 0.15},
        {"field": "deposit_amount", "name": "押金金额", "required": True, "weight": 0.20},
        {"field": "deduction_reason", "name": "扣款原因", "required": True, "weight": 0.20},
        {"field": "contract_status", "name": "合同状态", "required": True, "weight": 0.15},
        {"field": "landlord_attitude", "name": "房东态度", "required": False, "weight": 0.10},
        {"field": "has_communication", "name": "是否沟通过", "required": False, "weight": 0.10},
        {"field": "has_check_in_photo", "name": "是否有入住照片", "required": False, "weight": 0.05},
        {"field": "has_check_out_record", "name": "是否有退房验收记录", "required": False, "weight": 0.05}
    ]
    # 其他 case_type 同理
}
```

#### 输出

```json
{
  "completeness": {
    "score": 0.85,
    "total_fields": 8,
    "filled_fields": 6,
    "missing_fields": [
      {"field": "has_check_in_photo", "name": "入住照片", "weight": 0.05},
      {"field": "has_check_out_record", "name": "退房验收记录", "weight": 0.05}
    ],
    "need_follow_up": false,
    "threshold": 0.80
  }
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| extracted_info 全为 null | 完整度 0%，触发追问 |
| case_type 为 UNKNOWN | 加载通用要素清单（角色、金额、争议点、时间） |
| LLM 灰度判断超时 | 直接按规则层结果走，不阻塞流程 |
| 阈值设置过严导致死循环 | 最多追问 3 轮，3 轮后强制进入节点5 |

#### 技术实现

| 项目 | 选型 |
|------|------|
| 规则引擎 | 纯 Python，无第三方依赖 |
| 要素清单 | 配置文件（YAML / Python dict），按 case_type 索引 |
| LLM 灰度判断 | DeepSeek API，仅当 60% ≤ score < 80% 时调用 |
| 阈值配置 | 0.80（可配置，通过环境变量调整） |

---

### 2.4 节点4：追问生成（LLM）

#### 节点定位
当节点3 判定信息不足时，把缺失字段翻译成自然语言追问，引导用户补充。**追问的好坏直接影响用户体验和信息补充效果。**

#### 输入

```json
{
  "case_type": "DEPOSIT",
  "missing_fields": [
    {"field": "has_check_in_photo", "name": "入住照片"},
    {"field": "has_check_out_record", "name": "退房验收记录"}
  ],
  "extracted_info": {
    "role": "tenant",
    "deposit_amount": 3000,
    "deduction_reason": "墙面损坏",
    "contract_status": "expired"
  },
  "round": 1
}
```

#### 处理逻辑

1. 把缺失字段 + 已有信息组装 Prompt
2. 调用 LLM 生成自然语言追问，要求：
   - 一次最多问 3 个问题（避免用户疲劳）
   - 优先问权重高的字段
   - 用口语化表达，不要说"请提供 has_check_in_photo 字段"
   - 结合已有信息，让追问更有针对性
3. 输出追问文本，前端展示给用户
4. 用户回答后，把回答拼接到 description 后，重新进入节点2

#### Prompt 示例

```
你是一名租房纠纷咨询助手。根据已掌握的信息和缺失的字段，生成自然语言追问。

【已知信息】
- 用户角色：租客
- 押金金额：3000元
- 扣款原因：墙面损坏
- 合同状态：已到期

【缺失字段】
1. 入住照片
2. 退房验收记录

【生成要求】
1. 一次最多问 3 个问题
2. 口语化，像朋友聊天
3. 不要透露字段技术名
4. 结合已知信息让追问更精准（如"您提到墙面损坏，那入住时拍过照片吗？"）

【输出格式】
直接输出追问文本，不要任何前后缀。

【示例】
"为了更准确分析您的情况，请补充以下信息：
1. 您入住时是否拍摄过房屋照片？
2. 退房时是否和房东做过验收记录？"
```

#### 输出

```json
{
  "follow_up_question": "为了更准确分析您的情况，请补充以下信息：\n1. 您入住时是否拍摄过房屋照片？\n2. 退房时是否和房东一起做过验收记录，是否有书面或聊天记录？",
  "round": 1
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| LLM 返回过长追问 | 截断到前 200 字 |
| 追问轮数 ≥ 3 | 强制结束循环，进入节点5（用已有信息生成报告，标记"信息不完整"） |
| 用户回答"不知道/没有" | 仍记录为已填，但值为 unknown，避免重复追问 |
| LLM 失败 | 用模板兜底："请补充以下信息：1. {missing_field_1} 2. {missing_field_2}" |

#### 技术实现

| 项目 | 选型 |
|------|------|
| LLM | DeepSeek API |
| 追问轮数控制 | CaseContext 中维护 `round` 计数器 |
| 模板兜底 | Python 字符串模板 |
| 用户回答处理 | 追加到 description 字段后，触发节点2 重跑 |

---

### 2.5 节点5：RAG 知识检索（Embedding + FAISS）

#### 节点定位
从租房法律知识库中检索与当前纠纷相关的法条和案例，作为节点6 报告生成的"事实依据"。**这是防止 LLM 幻觉的核心节点。**

#### 输入

```json
{
  "case_type": "DEPOSIT",
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
  "extracted_info": {
    "deposit_amount": 3000,
    "deduction_reason": "墙面损坏",
    "contract_status": "expired"
  }
}
```

#### 处理逻辑

1. **Query 构造：** 把 case_type + description 关键词 + extracted_info 关键字段拼成检索 Query
   - 示例 Query：`"租房押金退还 墙面损坏 正常损耗 维修责任 押金不退"`
2. **Query 向量化：** 调用 Embedding 模型，把 Query 转成 768 维向量
3. **FAISS 检索：** 在预构建的 FAISS 索引中检索 Top-K（K=5）最相似的法律文档片段
4. **过滤：** 相似度 < 0.5 的结果丢弃，避免引入无关法条
5. **去重：** 同一条法条多次命中只保留相关度最高的一条

#### 知识库结构

```
知识库（独立于 MySQL，存为本地文件）
│
├── faiss_index.bin         # FAISS 索引文件
├── documents.json          # 文档原文（按 id 索引）
│
└── 数据来源：
    ├── 民法典合同编（租赁相关条款，约 30 条）
    ├── 房屋租赁合同示范文本
    ├── 常见租房纠纷案例集（约 50 个案例）
    ├── 证据收集指南
    └── 投诉处理流程文档
```

#### 输出

```json
{
  "rag_results": [
    {
      "doc_id": "law_710",
      "type": "law",
      "title": "民法典第710条",
      "content": "承租人按照约定的方法或者租赁物的性质使用租赁物，致使租赁物受到损耗的，不承担赔偿责任。",
      "score": 0.92,
      "relevance": "本条判定墙面损坏是否属于正常损耗，若属于正常损耗，房东不得扣除押金。"
    },
    {
      "doc_id": "law_713",
      "type": "law",
      "title": "民法典第713条",
      "content": "承租人在租赁物需要维修时可以请求出租人在合理期限内维修。出租人未履行维修义务的，承租人可以自行维修，维修费用由出租人负担。",
      "score": 0.87,
      "relevance": "涉及维修责任归属，若墙面损坏因房东未维修导致，租客不承担责任。"
    },
    {
      "doc_id": "case_023",
      "type": "case",
      "title": "李某诉王某房屋租赁合同纠纷案",
      "content": "租客退房时房东以墙面污损为由扣留押金，法院判决墙面污损属于正常损耗，房东应退还押金。",
      "score": 0.81,
      "relevance": "类似案件参考，法院倾向于认定墙面正常使用痕迹不属于扣款事由。"
    }
  ],
  "query": "租房押金退还 墙面损坏 正常损耗 维修责任 押金不退"
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| FAISS 索引加载失败 | 降级为空数组，节点6 报告中标记"未检索到相关法条" |
| 检索结果 < 3 条 | 放宽相似度阈值到 0.3；仍不足 3 条则补充通用法条 |
| Embedding 服务超时 | 重试 2 次；仍失败则降级为关键词检索（jieba 分词 + TF-IDF） |
| Query 过长 | 截取前 100 字向量化 |

#### 技术实现

| 项目 | 选型 |
|------|------|
| Embedding 模型 | `bge-small-zh-v1.5`（本地部署）或 OpenAI `text-embedding-3-small` |
| 向量库 | FAISS（`faiss-cpu`） |
| 知识库构建 | LangChain `TextSplitter` 切分文档 + Embedding 入库 |
| Query 构造 | 规则拼装（case_type 关键词 + extracted_info 关键字段） |
| 离线构建脚本 | 单独 Python 脚本，跑一次生成 faiss_index.bin |

---

### 2.6 节点6：分析报告生成（LLM + Prompt）

#### 节点定位
整合前 5 个节点的输出，生成最终的分析报告。**这是用户直接看到的产物，质量决定产品口碑。**

#### 输入

```json
{
  "case_type": "DEPOSIT",
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
  "extracted_info": {
    "role": "tenant",
    "deposit_amount": 3000,
    "deduction_reason": "墙面损坏",
    "contract_status": "expired",
    "landlord_attitude": "refused"
  },
  "completeness": {
    "score": 0.85,
    "missing_fields": [
      {"field": "has_check_in_photo", "name": "入住照片"},
      {"field": "has_check_out_record", "name": "退房验收记录"}
    ]
  },
  "rag_results": [
    {
      "title": "民法典第710条",
      "content": "承租人按照约定的方法...致使租赁物受到损耗的，不承担赔偿责任。",
      "relevance": "本条判定墙面损坏是否属于正常损耗..."
    },
    {
      "title": "民法典第713条",
      "content": "出租人应当履行租赁物的维修义务...",
      "relevance": "涉及维修责任归属..."
    }
  ]
}
```

#### 处理逻辑

1. 加载报告生成 Prompt 模板（固定 5 部分结构）
2. 把 extracted_info、missing_fields、rag_results 填入 Prompt
3. 调用 LLM 生成报告，要求严格输出 JSON
4. 后处理：校验报告 5 个部分字段是否齐全，缺失则补占位符

#### Prompt 模板

```
你是一名租房纠纷分析专家。请根据以下信息生成纠纷分析报告。

【用户纠纷描述】
{description}

【结构化信息】
- 纠纷类型：{case_type}
- 用户角色：{extracted_info.role}
- 押金金额：{extracted_info.deposit_amount} 元
- 扣款原因：{extracted_info.deduction_reason}
- 合同状态：{extracted_info.contract_status}
- 房东态度：{extracted_info.landlord_attitude}

【缺失信息】
{missing_fields}

【相关法条与案例（必须且只能引用这些，不得编造）】
{rag_results}

【输出格式（严格 JSON）】
{
  "summary": "纠纷事实摘要，2-3 句话",
  "risk_analysis": {
    "level": "LOW/MEDIUM/HIGH",
    "reasons": ["原因1", "原因2", "原因3"]
  },
  "key_disputes": [
    {"point": "争议点1", "description": "争议说明"},
    {"point": "争议点2", "description": "争议说明"}
  ],
  "missing_evidence": [
    {"name": "证据1", "priority": "HIGH/MEDIUM/LOW", "purpose": "作用"},
    {"name": "证据2", "priority": "HIGH/MEDIUM/LOW", "purpose": "作用"}
  ],
  "action_plan": [
    {"step": 1, "action": "动作描述", "reason": "为什么做"},
    {"step": 2, "action": "动作描述", "reason": "为什么做"}
  ],
  "legal_basis": [
    {"law": "民法典第710条", "content": "原文", "application": "如何适用本案"}
  ]
}

【硬性约束】
1. legal_basis 中的法条必须来自上面提供的【相关法条与案例】，不得编造
2. risk_analysis.level 必须给出至少 2 条 reasons
3. action_plan 必须是具体可操作的步骤，不要说"咨询律师"这种空话
4. missing_evidence 至少 1 条
5. 不要输出任何 JSON 以外的内容
```

#### 输出

```json
{
  "report": {
    "summary": "用户租赁合同到期后退房，房东以墙面损坏为由拒绝返还 3000 元押金，双方未达成一致。",
    "risk_analysis": {
      "level": "MEDIUM",
      "reasons": [
        "房东存在扣款理由（墙面损坏），但未提供维修费用证明",
        "用户目前缺少入住照片和退房验收记录，举证困难",
        "合同已到期，押金应按约定退还，房东拒退存在违约风险"
      ]
    },
    "key_disputes": [
      {"point": "墙面损坏责任", "description": "是否属于正常损耗，是否由租客人为造成"},
      {"point": "维修费用真实性", "description": "房东未提供维修发票或报价单"},
      {"point": "押金扣除合理性", "description": "是否符合合同约定的扣除条件"}
    ],
    "missing_evidence": [
      {"name": "入住时房屋照片", "priority": "HIGH", "purpose": "证明入住时墙面状态，对比退房时损坏"},
      {"name": "退房验收记录", "priority": "HIGH", "purpose": "证明退房时的房屋状态，避免事后争议"},
      {"name": "房东维修凭证", "priority": "MEDIUM", "purpose": "验证扣款金额真实性"}
    ],
    "action_plan": [
      {"step": 1, "action": "书面要求房东提供墙面维修费用证明（发票或报价单）", "reason": "无凭证则扣款缺乏依据"},
      {"step": 2, "action": "整理合同、转账记录、聊天记录作为基础证据", "reason": "证明租赁关系和押金支付"},
      {"step": 3, "action": "尝试与房东协商，提出按正常损耗处理", "reason": "民法典 710 条支持正常损耗免责"},
      {"step": 4, "action": "协商不成拨打 12345 或向住建部门投诉", "reason": "行政途径成本低、效率高"}
    ],
    "legal_basis": [
      {
        "law": "民法典第710条",
        "content": "承租人按照约定的方法或者租赁物的性质使用租赁物，致使租赁物受到损耗的，不承担赔偿责任。",
        "application": "若墙面损坏属于正常使用损耗，租客不担责，房东不得扣押金"
      },
      {
        "law": "民法典第713条",
        "content": "出租人应当履行租赁物的维修义务...",
        "application": "若墙面损坏因房东未及时维修导致，维修责任在房东"
      }
    ]
  }
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| LLM 输出非法 JSON | 正则提取 + 重试 1 次 |
| legal_basis 中出现 RAG 结果之外的法条 | 节点7 会校验，本节点不阻塞 |
| 报告字段缺失 | 后处理补占位符"暂无相关信息" |
| LLM 超时 | 重试 2 次；仍失败则用降级模板生成简版报告 |
| RAG 结果为空 | Prompt 中说明"未检索到相关法条"，要求 LLM 不引用任何法条 |

#### 技术实现

| 项目 | 选型 |
|------|------|
| LLM | DeepSeek API（建议用 `deepseek-chat`，比 `deepseek-coder` 更擅长写作） |
| Prompt 模板 | Jinja2 模板引擎，便于变量替换 |
| JSON 校验 | Pydantic Model 定义 `ReportSchema` |
| 降级模板 | 简版报告：summary + risk_analysis + action_plan 3 个字段 |

---

### 2.7 节点7：幻觉校验（规则校验）

#### 节点定位
报告生成后，校验报告中引用的法条是否真实存在于知识库。**这是防幻觉的最后一道防线，纯规则，不调用 LLM。**

#### 输入

```json
{
  "report": {
    "legal_basis": [
      {"law": "民法典第710条", "content": "承租人按照约定的方法..."},
      {"law": "民法典第713条", "content": "出租人应当履行维修义务..."},
      {"law": "民法典第888条", "content": "虚构的法条..."}
    ]
  },
  "rag_results": [
    {"title": "民法典第710条", "content": "..."},
    {"title": "民法典第713条", "content": "..."}
  ]
}
```

#### 处理逻辑

1. 从 report.legal_basis 中提取所有法条编号（用正则匹配"民法典第 XXX 条"格式）
2. 从知识库 documents.json 中加载所有真实法条编号集合
3. 逐条比对：
   - 编号存在且 content 一致 → 通过
   - 编号存在但 content 不一致 → 标记"内容存疑"，用知识库原文替换
   - 编号不存在 → 标记为幻觉，从报告中删除
4. 输出校验结果 + 修正后的报告

#### 校验代码逻辑

```python
# 伪代码
def check_hallucination(report, knowledge_base):
    real_laws = knowledge_base.get_all_law_titles()  # {"民法典第710条", ...}
    issues = []
    valid_laws = []

    for item in report["legal_basis"]:
        if item["law"] not in real_laws:
            issues.append({
                "law": item["law"],
                "issue": "法条编号不存在，疑似幻觉",
                "action": "deleted"
            })
        elif item["content"] != knowledge_base.get(item["law"]):
            issues.append({
                "law": item["law"],
                "issue": "法条内容与原文不符",
                "action": "replaced"
            })
            item["content"] = knowledge_base.get(item["law"])
            valid_laws.append(item)
        else:
            valid_laws.append(item)

    report["legal_basis"] = valid_laws  # 删除幻觉法条
    return {"passed": len(issues) == 0, "issues": issues, "report": report}
```

#### 输出

```json
{
  "hallucination_check": {
    "passed": false,
    "issues": [
      {
        "law": "民法典第888条",
        "issue": "法条编号不存在，疑似幻觉",
        "action": "deleted"
      }
    ],
    "total_checked": 3,
    "valid_count": 2,
    "hallucination_count": 1
  }
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| 知识库加载失败 | 跳过校验，报告原样输出，日志记录告警 |
| 报告中无法条引用 | 直接通过 |
| 法条编号格式不规范（如"民法典710条"缺"第"字） | 先正则规范化再比对 |
| 全部法条都是幻觉 | 删除全部，报告 legal_basis 置空，前端展示"未引用法条" |

#### 技术实现

| 项目 | 选型 |
|------|------|
| 法条编号提取 | Python `re` 正则 |
| 知识库比对 | Python set 集合操作 |
| 法条编号字典 | 启动时加载到内存，O(1) 查询 |
| 无 LLM 调用 | 纯规则，响应 < 50ms |

---

## 三、子工作流：AI 证据智能管理

### 3.1 子工作流总览图

```
                    用户上传文件 (图片/PDF/文本)
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点A：文件类型判断              │
              │  处理：后缀 + Magic Number        │
              │  输出：evidence_type              │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点B：OCR 内容提取              │
              │  图片 → Tesseract OCR            │
              │  PDF  → pdfplumber 文本解析       │
              │  输出：file_content (文本)        │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点C：关键信息提取 (LLM)        │
              │  按 evidence_type 选字段          │
              │  输出：extract_content (JSON)     │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点D：证据评分 (LLM + 规则)     │
              │  评估该证据对案件的重要性          │
              │  输出：importance_level + 作用    │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点E：证据目录生成              │
              │  汇总所有证据 + 缺失证据提示      │
              │  输出：证据目录 JSON              │
              └───────────────────────────────────┘
```

### 3.2 节点A：文件类型判断

#### 节点定位
判断用户上传的文件属于哪一类证据，决定后续 OCR 方式和信息提取字段。

#### 输入

```json
{
  "file_name": "租赁合同.pdf",
  "file_url": "/uploads/2026/08/合同.pdf",
  "file_extension": "pdf"
}
```

#### 处理逻辑

1. 一级判断：根据文件后缀
   - `.pdf` `.docx` → 倾向文档类
   - `.jpg` `.png` → 图片类
2. 二级判断：根据文件名关键词
   - 含"合同/租约/lease" → CONTRACT
   - 含"微信/聊天/记录" → CHAT
   - 含"转账/收据/付款" → PAYMENT
   - 含"照片/房屋/现场" → IMAGE
3. 三级判断（图片类）：若关键词无匹配，留待节点C LLM 判断

#### 输出

```json
{
  "evidence_type": "CONTRACT",
  "judge_method": "filename_keyword",
  "confidence": 0.9
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| 后缀和内容不匹配（如 .pdf 实为图片） | 节点B 解析失败后回退到节点A 重新判断 |
| 完全无法识别 | 默认 OTHER，节点C 用通用 Prompt |

#### 技术实现

| 项目 | 选型 |
|------|------|
| 后缀识别 | Python `os.path.splitext` |
| Magic Number | `python-magic` 库（可选，MVP 可省略） |
| 关键词字典 | Python dict，配置文件管理 |

---

### 3.3 节点B：OCR 内容提取

#### 节点定位
把图片/PDF 中的文字提取出来，供节点C LLM 理解。

#### 输入

```json
{
  "file_url": "/uploads/2026/08/合同.pdf",
  "evidence_type": "CONTRACT",
  "file_extension": "pdf"
}
```

#### 处理逻辑

1. 根据文件类型走不同解析路径：
   - **PDF（文本型）：** 用 `pdfplumber` 直接提取文本
   - **PDF（扫描型）：** 转图片后走 OCR
   - **图片：** 用 `Tesseract OCR` 识别中文
2. 文本清洗：去除多余空白、换行，保留段落结构
3. 输出纯文本

#### 输出

```json
{
  "file_content": "房屋租赁合同\n出租方：张三\n承租方：李四\n租赁期限：2026年1月1日至2026年12月31日\n月租金：3000元\n押金：3000元...",
  "ocr_confidence": 0.92,
  "char_count": 1528
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| PDF 解析失败 | 转图片走 OCR |
| OCR 置信度 < 0.5 | 标记"识别质量低"，节点D 评分降级 |
| 文件损坏 | 节点E 证据目录标记"解析失败" |
| 文件过大（>10MB） | 提示用户压缩后重传 |
| OCR 无文字 | file_content 置空，节点C 改为图像理解（可选接入多模态 LLM） |

#### 技术实现

| 项目 | 选型 |
|------|------|
| PDF 文本提取 | `pdfplumber` |
| 图片 OCR | `pytesseract` + 中文语言包 `chi_sim` |
| PDF 转图片 | `pdf2image` |
| 文本清洗 | Python `re` + 字符串处理 |
| 备选方案 | 阿里云 OCR / 腾讯云 OCR（精度更高，按量付费） |

---

### 3.4 节点C：关键信息提取（LLM）

#### 节点定位
把节点B 提取的纯文本，按证据类型转化为结构化信息。

#### 输入

```json
{
  "evidence_type": "CONTRACT",
  "file_content": "房屋租赁合同\n出租方：张三\n承租方：李四\n租赁期限：2026年1月1日至2026年12月31日...",
  "case_type": "DEPOSIT"
}
```

#### 处理逻辑

1. 根据 evidence_type 加载对应字段清单
   - CONTRACT → 租期、月租金、押金、违约条款、维修责任
   - CHAT → 时间、发送方、关键内容、争议点
   - PAYMENT → 金额、付款时间、付款方、收款方
   - IMAGE → 拍摄时间、场景描述
2. 把 file_content + 字段清单组装 Prompt
3. 调用 LLM 输出 JSON

#### Prompt 示例（CONTRACT 类型）

```
你是租房合同信息抽取助手。从合同文本中抽取以下字段。

【字段清单】
- lease_start：租期开始日期（YYYY-MM-DD）
- lease_end：租期结束日期（YYYY-MM-DD）
- monthly_rent：月租金（数字）
- deposit：押金（数字）
- breach_clause：违约条款摘要（字符串）
- maintenance_clause：维修责任条款摘要（字符串，无则填"未约定"）

【合同文本】
{file_content}

【输出格式（严格 JSON）】
{
  "lease_start": "2026-01-01",
  "lease_end": "2026-12-31",
  "monthly_rent": 3000,
  "deposit": 3000,
  "breach_clause": "提前退租扣1个月租金",
  "maintenance_clause": "未约定"
}

【规则】
1. 无法识别的字段填 null
2. 金额必须是数字
3. 不要输出额外说明
```

#### 输出

```json
{
  "extract_content": {
    "lease_start": "2026-01-01",
    "lease_end": "2026-12-31",
    "monthly_rent": 3000,
    "deposit": 3000,
    "breach_clause": "提前退租扣1个月租金",
    "maintenance_clause": "未约定"
  }
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| file_content 为空 | extract_content 置空，importance_level 降为 LOW |
| LLM 输出非 JSON | 同主工作流节点2 处理 |
| 字段类型错误 | Pydantic 校验，转换失败置 null |

#### 技术实现

| 项目 | 选型 |
|------|------|
| LLM | DeepSeek API |
| 字段清单 | Python dict，按 evidence_type 索引 |
| JSON 校验 | Pydantic Model |

---

### 3.5 节点D：证据评分（LLM + 规则）

#### 节点定位
评估单个证据对当前案件的重要性，决定在证据目录中的展示顺序。

#### 输入

```json
{
  "evidence_type": "CONTRACT",
  "extract_content": {
    "deposit": 3000,
    "breach_clause": "提前退租扣1个月租金"
  },
  "case_type": "DEPOSIT"
}
```

#### 处理逻辑

1. **规则层：** 按 evidence_type + case_type 组合查表，给出基础分
   - CONTRACT + DEPOSIT → HIGH（合同是押金纠纷核心证据）
   - CHAT + DEPOSIT → MEDIUM（辅助证据）
   - IMAGE + DEPOSIT → HIGH（现场照片关键）
2. **LLM 层：** 让 LLM 基于具体内容细化评分理由
3. 综合输出 importance_level 和作用说明

#### 评分规则表（部分）

| evidence_type | case_type=DEPOSIT | case_type=REPAIR | case_type=CONTRACT |
|---------------|-------------------|------------------|--------------------|
| CONTRACT | HIGH | HIGH | HIGH |
| PAYMENT | HIGH | MEDIUM | MEDIUM |
| CHAT | MEDIUM | MEDIUM | MEDIUM |
| IMAGE | HIGH | HIGH | LOW |
| VIDEO | HIGH | HIGH | LOW |
| OTHER | LOW | LOW | LOW |

#### 输出

```json
{
  "importance_level": "HIGH",
  "ai_summary": "本合同明确约定押金 3000 元、租期、违约条款，是判断押金是否应退还的核心依据。",
  "score_reason": "合同直接约定押金金额和退还条件，对押金纠纷案件具有决定性证明作用"
}
```

#### 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| evidence_type 或 case_type 缺失 | 默认 MEDIUM |
| LLM 失败 | 用规则层结果，ai_summary 用模板"该证据属于{evidence_type}类" |

#### 技术实现

| 项目 | 选型 |
|------|------|
| 规则表 | Python dict，配置文件管理 |
| LLM 评分 | DeepSeek API（可选，MVP 可只用规则） |
| 重要性枚举 | HIGH / MEDIUM / LOW |

---

### 3.6 节点E：证据目录生成

#### 节点定位
汇总一个案件下所有证据，按重要性排序，并对比案件类型应具备的证据清单，提示缺失项。

#### 输入

```json
{
  "case_id": 1001,
  "case_type": "DEPOSIT",
  "evidences": [
    {
      "id": 1,
      "file_name": "租赁合同.pdf",
      "evidence_type": "CONTRACT",
      "importance_level": "HIGH",
      "ai_summary": "合同约定押金 3000 元..."
    },
    {
      "id": 2,
      "file_name": "转账记录.jpg",
      "evidence_type": "PAYMENT",
      "importance_level": "HIGH",
      "ai_summary": "转账 3000 元给房东"
    }
  ]
}
```

#### 处理逻辑

1. 按 importance_level 排序：HIGH → MEDIUM → LOW
2. 加载该 case_type 的"应备证据清单"
3. 对比已有证据，找出缺失项
4. 输出证据目录 JSON

#### 应备证据清单（DEPOSIT）

```python
REQUIRED_EVIDENCE = {
    "DEPOSIT": [
        {"type": "CONTRACT", "name": "租赁合同", "must_have": True},
        {"type": "PAYMENT", "name": "押金支付记录", "must_have": True},
        {"type": "CHAT", "name": "沟通记录", "must_have": False},
        {"type": "IMAGE", "name": "入住/退房照片", "must_have": True}
    ]
}
```

#### 输出

```json
{
  "evidence_catalog": {
    "have_list": [
      {"id": 1, "file_name": "租赁合同.pdf", "type": "CONTRACT", "importance": "HIGH", "summary": "合同约定押金 3000 元..."},
      {"id": 2, "file_name": "转账记录.jpg", "type": "PAYMENT", "importance": "HIGH", "summary": "转账 3000 元给房东"}
    ],
    "missing_list": [
      {"type": "IMAGE", "name": "入住/退房照片", "must_have": true, "suggestion": "建议拍摄或找回入住时的房屋照片，用于对比墙面状态"},
      {"type": "CHAT", "name": "沟通记录", "must_have": false, "suggestion": "保存与房东关于押金退还的聊天记录"}
    ]
  }
}
```

#### 技术实现

| 项目 | 选型 |
|------|------|
| 应备清单 | Python dict 配置 |
| 排序 | Python `sorted` + 自定义 key |
| 无 LLM 调用 | 纯规则拼接 |

---

## 四、子工作流：AI 行动指南生成

### 4.1 子工作流总览图

```
              触发条件：用户点击"生成行动指南"
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点F：读取案件上下文            │
              │  读取：分析报告 + 证据列表 + 风险  │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点G：阶段判断 (规则)            │
              │  输出：当前阶段 (协商/投诉/诉讼)   │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点H：RAG 检索                  │
              │  检索：投诉渠道 / 法律程序 / 话术  │
              └───────────────┬───────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │  节点I：行动方案生成 (LLM)        │
              │  输出：行动步骤 + 话术 + 注意事项  │
              └───────────────────────────────────┘
```

### 4.2 节点F：读取案件上下文

#### 节点定位
从数据库读取已完成的分析报告和证据情况，作为行动方案的输入。**不重新分析，避免重复计算和结果不一致。**

#### 输入

```json
{
  "case_id": 1001
}
```

#### 处理逻辑

1. 查 `ai_report` 表最新版本报告
2. 查 `evidence` 表该案件所有证据
3. 查 `case_case` 表案件基本信息
4. 组装上下文 JSON

#### 输出

```json
{
  "case_context": {
    "case_type": "DEPOSIT",
    "risk_level": "MEDIUM",
    "report_summary": "用户租赁合同到期后...",
    "report_action_plan": [
      "要求房东提供维修凭证",
      "保存沟通记录"
    ],
    "evidence_completeness": 0.85,
    "missing_evidence": ["入住照片", "退房验收记录"],
    "has_evidence": true,
    "evidence_count": 2
  }
}
```

#### 技术实现

| 项目 | 选型 |
|------|------|
| 数据访问 | SQLAlchemy ORM |
| 报告版本 | 取 `version` 最大的记录 |

---

### 4.3 节点G：阶段判断（规则）

#### 节点定位
根据案件当前状态，判断用户处于"协商/投诉/诉讼"哪个阶段，决定行动方案的重点。

#### 输入

```json
{
  "case_context": {
    "risk_level": "MEDIUM",
    "has_evidence": true,
    "evidence_completeness": 0.85
  }
}
```

#### 处理逻辑

按规则表判断：

```python
def judge_stage(context):
    if not context["has_evidence"] or context["evidence_completeness"] < 0.5:
        return "EVIDENCE_COLLECTION"  # 证据收集阶段
    if context.get("negotiation_status") == "failed":
        return "COMPLAINT"  # 投诉阶段
    if context.get("complaint_status") == "failed":
        return "LITIGATION"  # 诉讼阶段
    return "NEGOTIATION"  # 默认协商阶段
```

#### 输出

```json
{
  "stage": "NEGOTIATION",
  "stage_name": "协商阶段",
  "stage_description": "建议先与房东协商解决，准备充分的证据和话术"
}
```

#### 技术实现

| 项目 | 选型 |
|------|------|
| 规则 | Python if-else |
| 阶段枚举 | EVIDENCE_COLLECTION / NEGOTIATION / COMPLAINT / LITIGATION |

---

### 4.4 节点H：RAG 检索

#### 节点定位
根据当前阶段，检索对应的行动知识（投诉渠道、法律程序、话术模板）。

#### 输入

```json
{
  "stage": "NEGOTIATION",
  "case_type": "DEPOSIT",
  "case_context": {
    "report_summary": "押金 3000 元不退..."
  }
}
```

#### 处理逻辑

1. 根据 stage 构造 Query
   - NEGOTIATION → "租房押金 协商话术 沟通技巧"
   - COMPLAINT → "租房纠纷 投诉渠道 12345 住建部门"
   - LITIGATION → "租房纠纷 起诉流程 小额诉讼"
2. 在 FAISS 索引中检索 Top-3
3. 返回相关知识

#### 输出

```json
{
  "action_rag_results": [
    {
      "title": "租房押金协商话术模板",
      "content": "您好，关于押金退还问题，根据《民法典》第710条...",
      "score": 0.88
    },
    {
      "title": "12345 投诉流程",
      "content": "拨打 12345 后说明情况...",
      "score": 0.72
    }
  ]
}
```

#### 技术实现

| 项目 | 选型 |
|------|------|
| 向量库 | 复用主工作流节点5 的 FAISS 索引 |
| Query 模板 | Python 字典，按 stage 索引 |

---

### 4.5 节点I：行动方案生成（LLM）

#### 节点定位
整合案件上下文 + 阶段 + RAG 检索结果，生成具体的、可执行的行动方案。

#### 输入

```json
{
  "case_context": {
    "case_type": "DEPOSIT",
    "risk_level": "MEDIUM",
    "report_summary": "押金 3000 元不退...",
    "missing_evidence": ["入住照片"]
  },
  "stage": "NEGOTIATION",
  "action_rag_results": [
    {"title": "协商话术模板", "content": "..."}
  ]
}
```

#### 处理逻辑

1. 加载行动方案 Prompt 模板
2. 填入案件上下文、阶段、RAG 结果
3. 调用 LLM 生成结构化行动方案

#### Prompt 模板

```
你是租房纠纷行动顾问。根据案件情况生成具体可执行的行动方案。

【案件情况】
- 纠纷类型：{case_type}
- 风险等级：{risk_level}
- 案件摘要：{report_summary}
- 缺失证据：{missing_evidence}
- 当前阶段：{stage}

【参考知识（话术和渠道）】
{action_rag_results}

【输出格式（严格 JSON）】
{
  "current_stage": "协商阶段",
  "steps": [
    {
      "step": 1,
      "title": "整理证据",
      "detail": "需要准备的证据清单",
      "estimated_time": "1-2天"
    },
    {
      "step": 2,
      "title": "联系房东",
      "detail": "具体沟通方式",
      "script": "AI 生成的话术模板"
    }
  ],
  "channels": [
    {"name": "12345 政务热线", "scenario": "协商不成时投诉", "cost": "免费"}
  ],
  "warnings": ["注意事项1", "注意事项2"]
}

【约束】
1. steps 必须具体可操作，不要"咨询律师"这种空话
2. script 字段必须给出完整话术
3. 引用的法条必须来自案件报告，不要编造
```

#### 输出

```json
{
  "action_guide": {
    "current_stage": "协商阶段",
    "steps": [
      {
        "step": 1,
        "title": "整理证据",
        "detail": "把合同、转账记录、聊天记录归类保存；尽快补拍入住时的房屋照片或寻找退房验收记录",
        "estimated_time": "1-2 天"
      },
      {
        "step": 2,
        "title": "书面联系房东",
        "detail": "通过微信或短信书面沟通，留存证据",
        "script": "您好，关于押金 3000 元退还问题，根据我们签订的租赁合同和《民法典》第 710 条，墙面正常使用损耗不属于扣款事由。请您提供维修费用证明，否则请在 7 日内退还押金，谢谢。"
      },
      {
        "step": 3,
        "title": "若协商不成，拨打 12345 投诉",
        "detail": "向住建部门或消费者协会投诉",
        "estimated_time": "3-7 个工作日"
      }
    ],
    "channels": [
      {"name": "12345 政务热线", "scenario": "协商不成时投诉", "cost": "免费"},
      {"name": "住建部门", "scenario": "房屋租赁纠纷行政调解", "cost": "免费"},
      {"name": "人民法院小额诉讼", "scenario": "金额较小、事实清楚的纠纷", "cost": "诉讼费 25-50 元"}
    ],
    "warnings": [
      "所有沟通尽量书面化，避免电话口头协商",
      "不要采取停水停电等过激行为",
      "保留所有证据原件"
    ]
  }
}
```

#### 技术实现

| 项目 | 选型 |
|------|------|
| LLM | DeepSeek API |
| Prompt 模板 | Jinja2 |
| JSON 校验 | Pydantic Model |

---

## 五、节点间数据流转（JSON 示例）

### 5.1 主工作流完整数据流

以下展示一个押金纠纷案例，从用户输入到最终报告的 CaseContext 完整演变过程。

#### Step 0：用户初始输入

```json
{
  "case_id": 1001,
  "user_id": 2001,
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
  "case_type": null,
  "intent": null,
  "extracted_info": null,
  "completeness": null,
  "missing_fields": null,
  "follow_up_question": null,
  "rag_results": null,
  "report": null,
  "hallucination_check": null,
  "round": 0
}
```

#### Step 1：经过节点1（意图识别）

```json
{
  "case_id": 1001,
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
  "case_type": "DEPOSIT",
  "intent": {
    "case_type": "DEPOSIT",
    "confidence": 0.93,
    "reason": "用户明确提到押金不退，属于押金纠纷"
  },
  "extracted_info": null,
  "round": 0
}
```

#### Step 2：经过节点2（信息抽取）

```json
{
  "case_id": 1001,
  "case_type": "DEPOSIT",
  "intent": {"case_type": "DEPOSIT", "confidence": 0.93},
  "extracted_info": {
    "role": "tenant",
    "deposit_amount": 3000,
    "deduction_reason": "墙面损坏",
    "contract_status": "expired",
    "landlord_attitude": "refused",
    "has_communication": true,
    "has_check_in_photo": null,
    "has_check_out_record": null
  },
  "round": 0
}
```

#### Step 3：经过节点3（完整度判断，假设 60% < score < 80%）

```json
{
  "completeness": {
    "score": 0.70,
    "total_fields": 8,
    "filled_fields": 5,
    "missing_fields": [
      {"field": "has_check_in_photo", "name": "入住照片", "weight": 0.05},
      {"field": "has_check_out_record", "name": "退房验收记录", "weight": 0.05}
    ],
    "need_follow_up": true,
    "threshold": 0.80
  }
}
```

#### Step 4：经过节点4（追问生成）

```json
{
  "follow_up_question": "为了更准确分析您的情况，请补充：\n1. 入住时是否拍摄过房屋照片？\n2. 退房时是否和房东做过验收记录？",
  "round": 1
}
```

> 用户回答："入住时拍过几张照片，退房时房东没要求验收。" → 拼接到 description 后重新进入节点2。

#### Step 5：再次经过节点2 + 节点3（完整度 ≥ 80%）

```json
{
  "extracted_info": {
    "role": "tenant",
    "deposit_amount": 3000,
    "deduction_reason": "墙面损坏",
    "contract_status": "expired",
    "landlord_attitude": "refused",
    "has_communication": true,
    "has_check_in_photo": true,
    "has_check_out_record": false
  },
  "completeness": {
    "score": 0.95,
    "need_follow_up": false
  }
}
```

#### Step 6：经过节点5（RAG 检索）

```json
{
  "rag_results": [
    {"doc_id": "law_710", "title": "民法典第710条", "content": "承租人...不承担赔偿责任。", "score": 0.92},
    {"doc_id": "law_713", "title": "民法典第713条", "content": "出租人应当履行维修义务...", "score": 0.87}
  ]
}
```

#### Step 7：经过节点6（报告生成）

```json
{
  "report": {
    "summary": "用户租赁合同到期后退房，房东以墙面损坏为由拒绝返还 3000 元押金。",
    "risk_analysis": {"level": "MEDIUM", "reasons": ["..."]},
    "key_disputes": [{"point": "墙面损坏责任", "description": "..."}],
    "missing_evidence": [{"name": "退房验收记录", "priority": "HIGH"}],
    "action_plan": [{"step": 1, "action": "要求房东提供维修凭证", "reason": "..."}],
    "legal_basis": [
      {"law": "民法典第710条", "content": "...", "application": "..."},
      {"law": "民法典第888条", "content": "虚构法条...", "application": "..."}
    ]
  }
}
```

#### Step 8：经过节点7（幻觉校验）

```json
{
  "hallucination_check": {
    "passed": false,
    "issues": [
      {"law": "民法典第888条", "issue": "法条编号不存在", "action": "deleted"}
    ]
  },
  "report": {
    "legal_basis": [
      {"law": "民法典第710条", "content": "...", "application": "..."}
    ]
  }
}
```

> 最终输出给用户的报告 = 校验后的 report。

### 5.2 证据管理子工作流数据流

```json
// 节点A 输出
{"evidence_type": "CONTRACT", "confidence": 0.9}

// 节点B 输出
{"file_content": "房屋租赁合同\n出租方：张三...", "ocr_confidence": 0.92}

// 节点C 输出
{"extract_content": {"lease_start": "2026-01-01", "deposit": 3000, "maintenance_clause": "未约定"}}

// 节点D 输出
{"importance_level": "HIGH", "ai_summary": "合同明确约定押金 3000 元..."}

// 节点E 输出（汇总）
{"evidence_catalog": {"have_list": [...], "missing_list": [...]}}

// 写入数据库 evidence 表
{
  "case_id": 1001,
  "file_name": "租赁合同.pdf",
  "evidence_type": "CONTRACT",
  "importance_level": "HIGH",
  "ai_summary": "合同明确约定押金 3000 元...",
  "extract_content": "{\"lease_start\":\"2026-01-01\",\"deposit\":3000}"
}
```

### 5.3 行动指南子工作流数据流

```json
// 节点F 输出
{"case_context": {"case_type": "DEPOSIT", "risk_level": "MEDIUM", "report_summary": "..."}}

// 节点G 输出
{"stage": "NEGOTIATION", "stage_name": "协商阶段"}

// 节点H 输出
{"action_rag_results": [{"title": "协商话术模板", "content": "...", "score": 0.88}]}

// 节点I 输出
{"action_guide": {"current_stage": "协商阶段", "steps": [...], "channels": [...], "warnings": [...]}}
```

---

## 六、设计决策说明表（面试可讲）

| 编号 | 设计决策 | 为什么这样设计 | 不这样设计的后果 | 面试加分话术 |
|------|---------|---------------|-----------------|-------------|
| 1 | 多节点串联而非单次 LLM 调用 | 每步可独立验证、独立优化、独立降级 | 单次调用幻觉严重，无法针对单步优化 | "我们把 Agent 拆成 7 个节点，每个节点有明确的输入输出契约，便于效果评估和迭代" |
| 2 | 节点3 完整度判断 + 节点4 追问循环 | 模拟律师咨询过程，信息越完整分析越准 | 信息不全导致报告质量差，用户体验差 | "我们用追问循环把信息完整度从 60% 提升到 80%+，这是产品体验的关键差异点" |
| 3 | 节点5 RAG 检索放在报告生成前 | LLM 只做整合不做回忆，从源头防幻觉 | LLM 凭记忆引用法条，常出现不存在的条文 | "RAG 是防幻觉的第一道防线，我们让 LLM 只基于检索结果整合，而不是凭记忆生成" |
| 4 | 节点7 幻觉校验作为独立节点 | 即使前面出错也能拦住，最后一道防线 | 错误法条流向用户，损害产品专业度 | "我们用纯规则做法条编号校验，0 LLM 调用，响应 < 50ms，这是成本最低的防线" |
| 5 | 节点3 用规则 + LLM 混合判断 | 规则保证确定性，LLM 处理灰度区间 | 纯规则太机械，纯 LLM 不可控 | "完整度判断我们用规则做主判断，LLM 只在 60%-80% 灰度区间介入，兼顾准确性和成本" |
| 6 | CaseContext 作为节点间通信协议 | 节点解耦，便于独立测试和重试 | 节点间强耦合，改一个节点牵一发动全身 | "我们设计了 CaseContext 数据结构，每个节点只读自己需要的字段，写回自己产出的字段" |
| 7 | 证据管理用 OCR + LLM 组合 | OCR 负责"看到"，LLM 负责"看懂" | 纯 OCR 无法理解语义，纯 LLM 无法处理图片 | "我们用 OCR 把图片转文字，再用 LLM 抽取结构化字段，各司其职" |
| 8 | 行动指南读取案件上下文而非重新分析 | 避免重复计算，保证建议与分析报告一致 | 重新分析可能得出不一致的结论，用户困惑 | "行动指南节点 F 直接读已生成的报告，保证建议和分析的一致性，也节省了 LLM 调用成本" |
| 9 | 节点5 RAG 检索结果带 relevance 字段 | 帮助节点6 LLM 理解法条如何适用本案 | LLM 可能误用法条 | "我们在 RAG 结果中附加 relevance 字段，提示 LLM 这条法条如何适用于当前案件" |
| 10 | 追问最多 3 轮强制结束 | 避免死循环，保证用户耐心 | 用户被问烦了直接离开 | "我们设置追问轮数上限 3 轮，3 轮后强制生成报告并标记信息不完整，平衡准确性和体验" |
| 11 | 每个节点写 ai_task 表 | 记录每次 LLM 调用的输入输出和耗时，支撑效果评估 | 无法量化评估 AI 效果，无法迭代优化 | "我们用 ai_task 表记录每个节点的 Prompt、Response、Latency，这是 AI 效果评估的数据基础" |
| 12 | 节点6 报告生成用 Pydantic 校验 | 保证输出结构稳定，前端能稳定渲染 | LLM 偶尔输出缺字段，前端崩溃 | "我们用 Pydantic Model 校验报告结构，缺字段自动补占位符，保证前端稳定渲染" |

---

## 七、技术实现方案

### 7.1 技术栈选型

| 层级 | 技术选型 | 用途 | 备选方案 |
|------|---------|------|---------|
| LLM | DeepSeek API (`deepseek-chat`) | 节点 1/2/4/6/C/D/I 的 LLM 调用 | OpenAI GPT-4o-mini / 通义千问 |
| Embedding | `bge-small-zh-v1.5`（本地） | 节点5 Query 和文档向量化 | OpenAI `text-embedding-3-small` |
| 向量库 | FAISS (`faiss-cpu`) | 节点5 法律知识库检索 | Chroma / Milvus |
| OCR | Tesseract (`pytesseract`) + `chi_sim` | 节点B 图片文字识别 | 阿里云 OCR / 腾讯云 OCR |
| PDF 解析 | `pdfplumber` | 节点B PDF 文本提取 | PyPDF2 / pdfminer |
| LLM 编排 | LangChain | Prompt 管理、输出解析、重试 | LlamaIndex / 纯 SDK |
| 后端框架 | FastAPI | API 接口、Agent 编排 | Flask / Django |
| 数据库 | MySQL | 业务数据存储 | PostgreSQL |
| ORM | SQLAlchemy | 数据库访问 | Tortoise ORM |
| 数据校验 | Pydantic | JSON 结构校验 | marshmallow |
| 重试 | `tenacity` | LLM 调用失败重试 | 自实现 |
| 模板引擎 | Jinja2 | Prompt 模板渲染 | f-string |
| 文件存储 | 本地 / 阿里云 OSS | 证据文件存储 | MinIO / 七牛云 |
| 配置管理 | `python-dotenv` + YAML | 环境变量 + 要素清单配置 | Apollo / Nacos |

### 7.2 各节点技术实现

| 节点 | 核心库 | 关键代码模块 | LLM 调用 | 平均耗时 |
|------|--------|-------------|---------|---------|
| 1 意图识别 | langchain + openai | `agents/intent_agent.py` | 1 次 | 1-2s |
| 2 信息抽取 | langchain + pydantic | `agents/extract_agent.py` | 1 次 | 2-3s |
| 3 完整度判断 | 纯 Python + langchain | `agents/completeness_agent.py` | 0-1 次 | 0.1-2s |
| 4 追问生成 | langchain | `agents/followup_agent.py` | 1 次 | 1-2s |
| 5 RAG 检索 | faiss + sentence-transformers | `agents/rag_agent.py` | 0 次 | 0.2-0.5s |
| 6 报告生成 | langchain + jinja2 | `agents/report_agent.py` | 1 次 | 3-5s |
| 7 幻觉校验 | 纯 Python + re | `agents/hallucination_agent.py` | 0 次 | < 0.05s |
| A 文件类型 | 纯 Python | `evidence/file_type_agent.py` | 0 次 | < 0.05s |
| B OCR 提取 | pytesseract + pdfplumber | `evidence/ocr_agent.py` | 0 次 | 1-5s |
| C 信息提取 | langchain + pydantic | `evidence/extract_agent.py` | 1 次 | 2-3s |
| D 证据评分 | 纯 Python + langchain | `evidence/score_agent.py` | 0-1 次 | 0.1-2s |
| E 目录生成 | 纯 Python | `evidence/catalog_agent.py` | 0 次 | < 0.05s |
| F 读取上下文 | sqlalchemy | `action/context_agent.py` | 0 次 | 0.1s |
| G 阶段判断 | 纯 Python | `action/stage_agent.py` | 0 次 | < 0.01s |
| H RAG 检索 | faiss | `action/rag_agent.py` | 0 次 | 0.2-0.5s |
| I 方案生成 | langchain + jinja2 | `action/guide_agent.py` | 1 次 | 3-5s |

> **单次主工作流总耗时（无追问）：** 约 7-13 秒；含 1 轮追问约 10-17 秒。

### 7.3 工程目录结构建议

```
backend/
├── app/
│   ├── agents/                          # Agent 节点实现
│   │   ├── __init__.py
│   │   ├── base.py                      # BaseAgent 基类（含重试、日志、ai_task 记录）
│   │   ├── intent_agent.py              # 节点1：意图识别
│   │   ├── extract_agent.py             # 节点2：信息抽取
│   │   ├── completeness_agent.py        # 节点3：完整度判断
│   │   ├── followup_agent.py            # 节点4：追问生成
│   │   ├── rag_agent.py                 # 节点5：RAG 检索
│   │   ├── report_agent.py              # 节点6：报告生成
│   │   ├── hallucination_agent.py       # 节点7：幻觉校验
│   │   └── orchestrator.py              # 主工作流编排器
│   │
│   ├── evidence/                        # 证据管理子工作流
│   │   ├── __init__.py
│   │   ├── file_type_agent.py           # 节点A
│   │   ├── ocr_agent.py                 # 节点B
│   │   ├── extract_agent.py             # 节点C
│   │   ├── score_agent.py               # 节点D
│   │   └── catalog_agent.py             # 节点E
│   │
│   ├── action/                          # 行动指南子工作流
│   │   ├── __init__.py
│   │   ├── context_agent.py             # 节点F
│   │   ├── stage_agent.py               # 节点G
│   │   ├── rag_agent.py                 # 节点H
│   │   └── guide_agent.py               # 节点I
│   │
│   ├── prompts/                         # Prompt 模板
│   │   ├── intent.j2
│   │   ├── extract_deposit.j2
│   │   ├── extract_repair.j2
│   │   ├── followup.j2
│   │   ├── report.j2
│   │   └── action_guide.j2
│   │
│   ├── config/                          # 配置文件
│   │   ├── required_fields.yaml         # 各 case_type 的抽取字段清单
│   │   ├── completeness_rules.yaml      # 完整度要素清单
│   │   ├── evidence_score_rules.yaml    # 证据评分规则表
│   │   └── required_evidence.yaml       # 应备证据清单
│   │
│   ├── rag/                             # RAG 知识库
│   │   ├── build_index.py               # 离线构建 FAISS 索引脚本
│   │   ├── knowledge_docs/              # 法律文档原文
│   │   │   ├── civil_law.md
│   │   │   ├── cases.md
│   │   │   └── complaint_guide.md
│   │   ├── faiss_index.bin              # FAISS 索引（运行时生成）
│   │   └── documents.json               # 文档原文映射
│   │
│   ├── models/                          # 数据模型
│   │   ├── entities.py                  # SQLAlchemy ORM 模型
│   │   └── schemas.py                   # Pydantic 数据校验模型
│   │
│   ├── core/                            # 基础设施
│   │   ├── config.py                    # 全局配置
│   │   ├── llm_client.py                # LLM 调用封装
│   │   ├── embedding_client.py          # Embedding 调用封装
│   │   └── logger.py                    # 日志
│   │
│   └── api/                             # API 路由
│       ├── routes/
│       │   ├── case.py                  # 案件相关接口
│       │   ├── evidence.py              # 证据相关接口
│       │   └── action.py                # 行动指南接口
│       └── router.py
│
├── requirements.txt
└── .env.example
```

### 7.4 异常与重试机制

#### 7.4.1 LLM 调用重试策略

```python
# core/llm_client.py 伪代码
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMClient:
    @retry(
        stop=stop_after_attempt(3),              # 最多重试 3 次
        wait=wait_exponential(multiplier=1, min=1, max=10),  # 指数退避 1s/2s/4s
        retry=retry_if_exception_type((TimeoutError, RateLimitError))
    )
    def chat(self, prompt: str, response_format: dict = None) -> str:
        # 调用 DeepSeek API
        pass
```

#### 7.4.2 节点级降级策略

| 节点 | 重试次数 | 降级方案 |
|------|---------|---------|
| 1 意图识别 | 2 | 降级为 UNKNOWN，前端引导用户手动选择 |
| 2 信息抽取 | 2 | 输出空 JSON，依赖节点3 触发追问 |
| 3 完整度判断 | 不重试 | 跳过 LLM 灰度判断，纯规则结果 |
| 4 追问生成 | 1 | 用模板兜底 |
| 5 RAG 检索 | 2 | 返回空数组，报告标记"未检索到法条" |
| 6 报告生成 | 3 | 降级为简版模板报告 |
| 7 幻觉校验 | 不重试 | 跳过校验，原样输出报告 |
| B OCR | 1 | file_content 置空，importance 降级 |

#### 7.4.3 主工作流异常兜底

```python
# agents/orchestrator.py 伪代码
class MainOrchestrator:
    def run(self, case_context: CaseContext) -> CaseContext:
        try:
            case_context = self.intent_agent.run(case_context)
            case_context = self.extract_agent.run(case_context)
            case_context = self.completeness_agent.run(case_context)

            # 追问循环（最多 3 轮）
            while case_context.completeness.need_follow_up and case_context.round < 3:
                case_context = self.followup_agent.run(case_context)
                # 等待用户回答（异步）
                return case_context  # 返回给前端，等用户补充后再次调用

            case_context = self.rag_agent.run(case_context)
            case_context = self.report_agent.run(case_context)
            case_context = self.hallucination_agent.run(case_context)

            return case_context

        except Exception as e:
            logger.error(f"主工作流异常: {e}", exc_info=True)
            case_context.report = self.fallback_report(case_context, str(e))
            return case_context
```

### 7.5 可观测性与效果评估

#### 7.5.1 ai_task 表记录

每次 LLM 调用都写入 `ai_task` 表，对应数据库设计文档中的 ai_task 表：

```python
# agents/base.py 伪代码
class BaseAgent:
    def run(self, case_context: CaseContext) -> CaseContext:
        start_time = time.time()
        task_record = AITask(
            case_id=case_context.case_id,
            task_type=self.task_type,  # 如 INTENT / EXTRACT / RAG
            prompt=self.render_prompt(case_context),
            status="RUNNING",
        )
        db.add(task_record)
        db.commit()

        try:
            response = self.llm_client.chat(task_record.prompt)
            task_record.response = response
            task_record.status = "SUCCESS"
            task_record.latency = int((time.time() - start_time) * 1000)
        except Exception as e:
            task_record.status = "FAILED"
            task_record.response = str(e)
            raise
        finally:
            db.commit()

        return self.parse_response(response, case_context)
```

#### 7.5.2 效果评估指标

| 评估维度 | 指标 | 数据来源 | 评估方法 |
|---------|------|---------|---------|
| 意图识别准确率 | case_type 与人工标注一致的比例 | ai_task 表 INTENT 记录 | 抽样人工标注 100 条对比 |
| 信息抽取完整率 | extracted_info 非 null 字段比例 | ai_task 表 EXTRACT 记录 | 统计字段填充率 |
| 追问必要性 | 追问后完整度提升幅度 | ai_task 表 COMPLETENESS 记录 | 对比追问前后 score |
| RAG 检索相关性 | Top-5 中相关文档占比 | ai_task 表 RAG 记录 | 抽样人工评估 |
| 报告生成质量 | 法条引用准确率 + 用户反馈 | ai_task 表 REPORT + 用户反馈 | 幻觉校验结果 + 用户评分 |
| 幻觉拦截率 | 节点7 拦截的幻觉数 / 报告法条总数 | ai_task 表 REPORT + 节点7 日志 | 统计拦截比例 |
| 系统性能 | 各节点平均耗时 | ai_task 表 latency 字段 | P50 / P95 统计 |

#### 7.5.3 日志规范

每个节点输出结构化日志，便于排查：

```python
logger.info({
    "event": "agent_run",
    "case_id": case_context.case_id,
    "agent": "intent_agent",
    "round": case_context.round,
    "input_length": len(case_context.description),
    "output": case_context.intent,
    "latency_ms": 1200,
    "status": "success"
})
```

---

## 附录：术语表

| 术语 | 含义 |
|------|------|
| Agent | AI 智能体节点，负责一个独立的 AI 任务 |
| CaseContext | 案件上下文，节点间传递的 JSON 数据结构 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| Embedding | 把文本转成向量，用于相似度检索 |
| FAISS | Facebook 开源的向量相似度检索库 |
| OCR | Optical Character Recognition，光学字符识别 |
| Hallucination | LLM 幻觉，指模型生成不存在的事实 |
| Prompt | 提示词，给 LLM 的输入指令 |
| Token | LLM 计费单位，约等于 1.5 个汉字 |
| Top-K | 检索结果中相似度最高的 K 条 |

---

*文档版本：V1.0*
*创建时间：2026-08-05*
*产品名称：租安 AI*
*阶段：AI Agent 流程设计（完成）*
