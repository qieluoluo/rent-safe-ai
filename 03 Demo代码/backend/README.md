# 后端

FastAPI 服务，包含 SQLAlchemy 数据模型、自动建表和基础 CRUD 接口。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## MySQL 配置

先在 MySQL 8.0 中创建数据库：

```sql
CREATE DATABASE rent_safe_ai DEFAULT CHARACTER SET utf8mb4;
```

然后在 `.env` 填写真实连接信息：

```env
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/rent_safe_ai?charset=utf8mb4
AUTO_CREATE_TABLES=true
```

服务启动时会自动创建 `user`、`case_case`、`evidence`、`ai_report`、`ai_task` 五张表。未配置 `.env` 时，服务使用本地 SQLite 便于开发验证。

- 健康检查：`http://localhost:8000/api/v1/health`
- API 文档：`http://localhost:8000/docs`

资源接口：`/api/v1/users`、`/cases`、`/evidences`、`/reports`、`/tasks`，均提供创建、列表、详情、更新和删除操作。

## 业务接口

以下接口统一返回 `{ "code": 0, "message": "success", "data": ... }`：

- `POST /api/cases`：创建案件
- `GET /api/cases`：分页获取案件列表
- `GET /api/cases/{case_id}`：查看案件详情
- `POST /api/evidence/upload`：上传证据（`multipart/form-data`，字段为 `case_id`、`file`、可选 `evidence_type`）
- `GET /api/evidence/{case_id}`：获取案件证据
- `GET /api/report/{case_id}`：获取案件最新报告
- `POST /api/cases/{case_id}/analysis`：运行六步 Mock 分析（同步返回）
- `GET /api/cases/{case_id}/analysis/tasks`：获取 Agent 工作流轨迹
