# 租安 AI（RentSafe AI）

> 面向租房**押金纠纷**的 AI 辅助决策 MVP — AI 产品经理实践项目

[![Demo Mode](https://img.shields.io/badge/AI-Demo%20Mock%20Baseline-amber)](03%20Demo代码/backend/app/agents/mock_provider.py)
[![Scope](https://img.shields.io/badge/Scope-Deposit%20Disputes-blue)](01%20产品文档/PRD核心功能详细设计.md)

## 项目简介

租安 AI 帮助普通租客将押金纠纷的自然语言描述，整理为**事实摘要、风险提示、证据缺口和下一步行动建议**。

- **产品定位：** AI 产品经理求职作品（个人项目）
- **V1 范围：** 仅押金纠纷黄金路径
- **当前 AI 模式：** 演示模式 · 规则 Mock 基线（`mock-v1.2`），非真实大模型
- **免责声明：** 输出为信息整理与风险提示，不构成法律意见

## 能力状态

| 能力 | 状态 |
|------|------|
| 六步 Agent 工作流 + 轨迹落库 | ✅ 已实现 |
| 前端可点击 Demo | ✅ 已实现 |
| Mock 评测 + Bad Case 回归 | ✅ 已实现（23 条合成用例） |
| 真实 LLM / 向量 RAG | 📋 规划中 |
| 用户登录 / OCR 证据解析 | 📋 规划中 |

## 快速开始

### 1. 后端（FastAPI）

```powershell
cd "03 Demo代码/backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

### 2. 前端（React + Vite）

```powershell
cd "03 Demo代码/frontend"
npm install
npm run dev
```

打开 http://localhost:5173 → **开始分析** → **填入演示样例** → **创建并分析**

### 3. Mock 评测

```powershell
python "04 AI效果验证/evaluate_mock.py"
```

## 仓库结构

```
├── 01 产品文档/          # PRD、用户研究（模拟数据已标注）、竞品分析
├── 02 技术设计/          # API、Agent 流程、Prompt、数据库
├── 03 Demo代码/          # frontend + backend 可运行代码
├── 04 AI效果验证/        # 评测脚本、合成测试集、Bad Case 记录
├── 05 作品集展示/        # 一页式案例、演示脚本（对外材料）
├── 06 项目过程与面试复盘/ # 开发日志、面试知识库（过程材料）
└── AGENTS.md             # 项目协作与诚信规范
```

## 演示路径

```text
描述押金纠纷 → 创建案件 → 触发六步分析 → 查看报告与行动建议 → 查看 Agent 轨迹
```

## 评测基线（Mock v1.2）

- 测试集：23 条脱敏合成用例（非真实用户数据）
- 结果：scope / amount / lease_status / reason / completeness 均为 100%（**仅规则基线**）
- 详见：[04 AI效果验证/README.md](04%20AI效果验证/README.md)

## 简历表述建议

**可以写：** MVP 定义、六步 Agent 设计、Mock 评测闭环、可演示 Demo

**不要写：** RAG 准确率 XX%、真实大模型已落地、50+ 真实用户案例（与仓库不符）

## 文档入口

- [一页式案例（作品集）](05%20作品集展示/01-项目一页式案例.md)
- [3 分钟演示脚本](05%20作品集展示/02-演示脚本.md)
- [能力证据索引](05%20作品集展示/03-能力证据索引.md)

## License

Personal portfolio project. Not for commercial legal advice use.
