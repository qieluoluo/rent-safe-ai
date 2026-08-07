# 租安 AI —— API 接口设计文档

> **文档类型：** MVP 接口规范
> **前置文档：** [产品需求分析.md](../产品文档/产品需求分析.md) ｜ [PRD核心功能详细设计.md](../产品文档/PRD核心功能详细设计.md) ｜ [数据库设计.md](数据库设计.md)
> **后端框架：** FastAPI + SQLAlchemy + Pydantic
> **版本：** V1.0
> **面向对象：** 前端开发、接入方开发、新人工程师

> **V1 实现说明（2026-08-07）：** 分析相关接口已实现为同步模式，路径为 `POST /api/cases/{case_id}/analysis` 和 `GET /api/cases/{case_id}/analysis/tasks`（非本文档原设计的异步 `/analyze` + `/analyze/status`）。以下接口总览表中标注了 V1 实际状态。

---

## 目录

```
一、接口规范说明
    1.1 基础信息
    1.2 统一响应格式
    1.3 分页响应格式
    1.4 错误码定义
    1.5 鉴权说明
    1.6 通用约定
二、接口总览
三、系统接口
    3.1 健康检查
四、用户认证接口
    4.1 用户注册
    4.2 用户登录
五、案件管理接口
    5.1 创建案件
    5.2 案件列表
    5.3 案件详情
六、证据管理接口
    6.1 上传证据
    6.2 获取案件证据列表
    6.3 证据 AI 处理
七、AI 分析接口
    7.1 触发 AI 纠纷分析
    7.2 查询 AI 分析状态
    7.3 获取最新分析报告
    7.4 获取历史报告列表
八、行动指南接口
    8.1 生成行动指南
九、合同风险检测接口
    9.1 合同风险分析
十、附录
    10.1 枚举值参考
    10.2 状态机说明
    10.3 错误码速查表
```

---

## 一、接口规范说明

### 1.1 基础信息

| 项目 | 说明 |
|------|------|
| 基础域名 | `http://localhost:8000`（本地开发） / `https://api.zuan-ai.com`（生产） |
| 接口前缀 | 业务接口统一挂载在 `/api` 前缀下；系统接口在 `/api/v1` 下 |
| 数据格式 | 请求与响应均使用 `application/json`；文件上传使用 `multipart/form-data` |
| 字符编码 | 统一 UTF-8 |
| 时间格式 | `YYYY-MM-DD HH:MM:SS`（如 `2026-08-05 14:30:00`） |
| 金额单位 | 元，保留两位小数（如 `3000.00`） |

### 1.2 统一响应格式

所有业务接口返回统一的 JSON 结构，包含三个固定字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，成功为 200，失败为对应错误码 |
| message | string | 状态描述信息，成功为 `success` |
| data | object / array / null | 业务数据，无数据时为 `null` |

**成功响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "case_title": "押金纠纷-房东拒退3000元"
  }
}
```

**失败响应示例：**

```json
{
  "code": 404,
  "message": "案件不存在",
  "data": null
}
```

### 1.3 分页响应格式

列表类接口统一采用分页结构，`data` 字段固定为以下结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| items | array | 当前页数据列表 |
| total | int | 数据总条数 |
| page | int | 当前页码，从 1 开始 |
| page_size | int | 每页条数，默认 20，最大 100 |

**分页响应示例：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {"id": 1, "case_title": "押金纠纷-房东拒退3000元"},
      {"id": 2, "case_title": "维修责任-水管漏水"}
    ],
    "total": 35,
    "page": 1,
    "page_size": 20
  }
}
```

**分页参数说明：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码，必须大于等于 1 |
| page_size | int | 否 | 20 | 每页条数，范围 1~100 |

### 1.4 错误码定义

错误码与 HTTP 状态码保持一致，常见错误码如下：

| 错误码 | 含义 | 触发场景 |
|--------|------|---------|
| 200 | 成功 | 请求处理成功 |
| 201 | 创建成功 | 资源创建类接口（POST）成功 |
| 400 | 参数错误 | 请求参数缺失、格式错误、业务校验失败 |
| 401 | 未授权 | 未携带 Token 或 Token 失效 |
| 404 | 资源未找到 | 路径中的 ID 在数据库中不存在 |
| 409 | 数据冲突 | 唯一约束冲突（如用户名重复）、删除关联数据失败 |
| 413 | 文件过大 | 上传文件超过 20MB 限制 |
| 415 | 不支持的媒体类型 | 上传文件后缀不在白名单内 |
| 422 | 参数校验失败 | Pydantic 字段校验未通过 |
| 500 | 服务器内部错误 | 服务异常、数据库错误、AI 调用失败 |

**错误响应示例：**

```json
{
  "code": 422,
  "message": "请求参数校验失败",
  "data": [
    {
      "loc": ["body", "amount"],
      "msg": "Input should be greater than or equal to 0",
      "type": "greater_than_equal"
    }
  ]
}
```

### 1.5 鉴权说明

| 接口类型 | 鉴权要求 |
|---------|---------|
| 健康检查 `GET /health` | 不需要鉴权 |
| 用户注册 `POST /auth/register` | 不需要鉴权 |
| 用户登录 `POST /auth/login` | 不需要鉴权 |
| 其他业务接口 | 需要鉴权 |

**鉴权方式：** Bearer Token（JWT）

在请求头中携带 Token：

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

> 说明：MVP 阶段鉴权能力会逐步接入。未启用鉴权时，所有接口可直接访问；启用后，未携带或携带无效 Token 的请求将返回 401。

### 1.6 通用约定

| 约定项 | 说明 |
|--------|------|
| ID 类型 | 所有主键 ID 均为整数（bigint），不带引号 |
| 必填字段 | 接口文档中标注「必填」的字段不可为空 |
| 枚举值 | 枚举字段使用大写下划线格式（如 `DEPOSIT`、`HIGH`） |
| 时间字段 | `create_time` 由服务端自动生成，请求无需传入 |
| 软删除 | MVP 阶段证据、报告等均使用物理删除，删除接口返回 204 |

---

## 二、接口总览

| 序号 | 方法 | 路径 | 功能 | 鉴权 | 状态 |
|------|------|------|------|------|------|
| 1 | GET | `/api/v1/health` | 健康检查 | 否 | 已实现 |
| 2 | POST | `/api/auth/register` | 用户注册 | 否 | 待实现 |
| 3 | POST | `/api/auth/login` | 用户登录 | 否 | 待实现 |
| 4 | POST | `/api/cases` | 创建案件 | 是 | 已实现 |
| 5 | GET | `/api/cases` | 案件列表（分页+筛选） | 是 | 已实现 |
| 6 | GET | `/api/cases/{case_id}` | 案件详情 | 是 | 已实现 |
| 7 | POST | `/api/evidence/upload` | 上传证据 | 是 | 已实现 |
| 8 | GET | `/api/evidence/{case_id}` | 获取案件证据列表 | 是 | 已实现 |
| 9 | POST | `/api/evidence/{evidence_id}/analyze` | 证据 AI 处理 | 是 | 待实现 |
| 10 | POST | `/api/cases/{case_id}/analysis` | 触发 AI 纠纷分析（同步） | 否（V1 Demo） | **已实现** |
| 11 | GET | `/api/cases/{case_id}/analysis/tasks` | 获取 AI Agent 工作流轨迹 | 否（V1 Demo） | **已实现** |
| 11b | GET | `/api/cases/{case_id}/analyze/status` | 查询 AI 分析状态（异步轮询） | 是 | 待实现（目标设计） |
| 12 | GET | `/api/report/{case_id}` | 获取最新分析报告 | 是 | 已实现 |
| 13 | GET | `/api/reports/{case_id}` | 获取历史报告列表 | 是 | 待实现 |
| 14 | POST | `/api/cases/{case_id}/action-plan` | 生成行动指南 | 是 | 待实现 |
| 15 | POST | `/api/contract/analyze` | 合同风险分析 | 是 | 待实现 |

---

## 三、系统接口

### 3.1 健康检查

**接口说明：** 用于本地启动检查和部署探针调用，验证服务是否正常运行。

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/api/v1/health` |
| 鉴权 | 否 |

**请求参数：** 无

**响应示例：**

```json
{
  "status": "ok"
}
```

> 说明：此接口返回结构较简化，不包含 `code/message/data` 三字段，仅供探针使用。

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 服务正常 |

---

## 四、用户认证接口

### 4.1 用户注册

**接口说明：** 用户通过用户名和密码注册账号。密码使用 PBKDF2-SHA256 加密存储。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/auth/register` |
| 鉴权 | 否 |
| Content-Type | `application/json` |

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名，长度 1~50，需唯一 |
| password | string | 是 | 密码，长度 6~255 |
| phone | string | 否 | 手机号，最长 20 字符 |
| avatar | string | 否 | 头像 URL，最长 255 字符 |

**请求示例：**

```json
{
  "username": "zhangsan",
  "password": "123456",
  "phone": "13800138000"
}
```

**响应示例（201）：**

```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "phone": "13800138000",
    "avatar": null,
    "create_time": "2026-08-05 14:30:00"
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 201 | 注册成功 |
| 400 | 用户名已存在 |
| 422 | 字段校验失败（如密码过短） |

---

### 4.2 用户登录

**接口说明：** 用户使用用户名和密码登录，成功后返回 JWT Token，后续请求需在 Header 中携带。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/auth/login` |
| 鉴权 | 否 |
| Content-Type | `application/json` |

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例：**

```json
{
  "username": "zhangsan",
  "password": "123456"
}
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxfQ.xxx",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "zhangsan",
      "phone": "13800138000",
      "avatar": null
    }
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 登录成功 |
| 400 | 用户名或密码错误 |
| 422 | 字段校验失败 |

---

## 五、案件管理接口

### 5.1 创建案件

**接口说明：** 用户创建一个租房纠纷案件。案件创建后默认状态为 `CREATED`，AI 分析状态为 `PENDING`。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/cases` |
| 鉴权 | 是 |
| Content-Type | `application/json` |

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | int | 是 | 用户 ID |
| case_title | string | 否 | 案件标题，最长 100 字符 |
| case_type | string | 是 | 纠纷类型，枚举：`DEPOSIT` / `RENT_CANCEL` / `REPAIR` / `CONTRACT` |
| description | string | 否 | 纠纷描述 |
| amount | number | 否 | 涉及金额（元），大于等于 0，最多两位小数 |
| status | string | 否 | 案件状态，默认 `CREATED` |
| risk_level | string | 否 | 风险等级：`LOW` / `MEDIUM` / `HIGH` |
| ai_status | string | 否 | AI 分析状态，默认 `PENDING` |

**请求示例：**

```json
{
  "user_id": 1,
  "case_title": "押金纠纷-房东拒退3000元",
  "case_type": "DEPOSIT",
  "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
  "amount": 3000.00
}
```

**响应示例（201）：**

```json
{
  "code": 200,
  "message": "案件创建成功",
  "data": {
    "id": 1,
    "user_id": 1,
    "case_title": "押金纠纷-房东拒退3000元",
    "case_type": "DEPOSIT",
    "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
    "amount": 3000.00,
    "status": "CREATED",
    "risk_level": null,
    "ai_status": "PENDING",
    "create_time": "2026-08-05 14:30:00"
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 201 | 案件创建成功 |
| 404 | user_id 对应的用户不存在 |
| 422 | 字段校验失败（如 case_type 为空） |

---

### 5.2 案件列表

**接口说明：** 分页查询案件列表，支持按用户、纠纷类型、案件状态筛选。结果按创建时间倒序排列。

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/api/cases` |
| 鉴权 | 是 |

**Query 参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码，大于等于 1 |
| page_size | int | 否 | 20 | 每页条数，1~100 |
| user_id | int | 否 | - | 用户 ID 筛选，大于 0 |
| case_type | string | 否 | - | 纠纷类型筛选，最长 50 字符 |
| case_status | string | 否 | - | 案件状态筛选，最长 20 字符 |

**请求示例：**

```
GET /api/cases?page=1&page_size=20&user_id=1&case_type=DEPOSIT
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "user_id": 1,
        "case_title": "押金纠纷-房东拒退3000元",
        "case_type": "DEPOSIT",
        "description": "房东以墙面损坏为由拒绝退还3000元押金",
        "amount": 3000.00,
        "status": "COMPLETED",
        "risk_level": "MEDIUM",
        "ai_status": "DONE",
        "create_time": "2026-08-05 14:30:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 查询成功 |
| 422 | 分页参数不合法 |

---

### 5.3 案件详情

**接口说明：** 根据 case_id 查询单个案件详情。

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/api/cases/{case_id}` |
| 鉴权 | 是 |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 案件 ID，大于 0 |

**请求示例：**

```
GET /api/cases/1
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "case_title": "押金纠纷-房东拒退3000元",
    "case_type": "DEPOSIT",
    "description": "我和房东签了一年合同，现在到期退房，但是房东说墙面有损坏，不退3000元押金。",
    "amount": 3000.00,
    "status": "ANALYZING",
    "risk_level": null,
    "ai_status": "PROCESSING",
    "create_time": "2026-08-05 14:30:00"
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 查询成功 |
| 404 | 案件不存在 |
| 422 | case_id 非法（小于 1） |

---

## 六、证据管理接口

### 6.1 上传证据

**接口说明：** 上传租房纠纷相关证据文件（合同、聊天截图、转账记录等）。文件本地存储，返回访问 URL。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/evidence/upload` |
| 鉴权 | 是 |
| Content-Type | `multipart/form-data` |

**Form 参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 关联案件 ID，大于 0 |
| file | file | 是 | 上传文件，支持 PDF / 图片 / Word / TXT，最大 20MB |
| evidence_type | string | 否 | 证据类型：`CONTRACT` / `PAYMENT` / `CHAT` / `IMAGE` / `VIDEO` / `OTHER`，未传则后续由 AI 自动识别 |

**允许的文件后缀：**

```
.pdf  .png  .jpg  .jpeg  .webp  .doc  .docx  .txt
```

**请求示例（curl）：**

```bash
curl -X POST http://localhost:8000/api/evidence/upload \
  -H "Authorization: Bearer {token}" \
  -F "case_id=1" \
  -F "file=@微信聊天截图.png" \
  -F "evidence_type=CHAT"
```

**响应示例（201）：**

```json
{
  "code": 200,
  "message": "证据上传成功",
  "data": {
    "id": 5,
    "case_id": 1,
    "file_name": "微信聊天截图.png",
    "file_url": "/uploads/a1b2c3d4e5f6.png",
    "file_type": "png",
    "evidence_type": "CHAT",
    "ai_summary": null,
    "importance_level": null
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 201 | 上传成功 |
| 404 | case_id 对应的案件不存在 |
| 413 | 文件超过 20MB |
| 415 | 文件后缀不在允许列表内 |
| 422 | 文件内容为空 |

---

### 6.2 获取案件证据列表

**接口说明：** 查询指定案件下的所有证据，按 ID 倒序排列（最新上传在前）。

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/api/evidence/{case_id}` |
| 鉴权 | 是 |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 案件 ID，大于 0 |

**请求示例：**

```
GET /api/evidence/1
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 5,
      "case_id": 1,
      "file_name": "退房视频.mp4",
      "file_url": "/uploads/f9e8d7c6b5a4.mp4",
      "file_type": "mp4",
      "evidence_type": "VIDEO",
      "ai_summary": "退房时墙面状态正常，无人为损坏",
      "importance_level": "HIGH"
    },
    {
      "id": 2,
      "case_id": 1,
      "file_name": "微信聊天截图.png",
      "file_url": "/uploads/a1b2c3d4e5f6.png",
      "file_type": "png",
      "evidence_type": "CHAT",
      "ai_summary": "房东表示扣除维修费用，但未提供凭证",
      "importance_level": "HIGH"
    }
  ]
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 查询成功 |
| 404 | 案件不存在 |
| 422 | case_id 非法 |

---

### 6.3 证据 AI 处理

**接口说明：** 触发 AI 对单个证据进行智能处理，包括：OCR 文字识别、关键信息提取、证据分类、重要程度评分。处理结果回写到证据记录。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/evidence/{evidence_id}/analyze` |
| 鉴权 | 是 |
| Content-Type | `application/json` |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| evidence_id | int | 是 | 证据 ID，大于 0 |

**请求示例：**

```
POST /api/evidence/2/analyze
```

请求体可为空，或携带可选参数：

```json
{
  "force": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| force | boolean | 否 | 是否强制重新处理（已处理过的证据是否覆盖），默认 false |

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "证据处理成功",
  "data": {
    "evidence_id": 2,
    "evidence_type": "CHAT",
    "ai_summary": "房东表示扣除维修费用，但未提供凭证",
    "importance_level": "HIGH",
    "extract_content": {
      "时间": "2026-07-20",
      "发送方": "房东",
      "关键内容": "墙面有损坏，扣除维修费2000元",
      "争议点": "房东单方面扣款，未提供维修凭证"
    },
    "task_id": 12
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 处理成功 |
| 404 | 证据不存在 |
| 500 | AI 调用失败 |

---

## 七、AI 分析接口

### 7.1 触发 AI 纠纷分析

> **V1 已实现：** 同步接口 `POST /api/cases/{case_id}/analysis`，立即返回完整分析结果（含 report 和 workflow）。以下为原异步设计，供后续版本参考。

**接口说明：** 触发对指定案件的 AI 纠纷智能分析。后端会异步执行：意图识别 → 信息抽取 → 完整度判断 → RAG 检索 → 报告生成 → 幻觉校验等节点。接口立即返回任务信息，前端通过状态查询接口轮询进度。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/cases/{case_id}/analyze` |
| 鉴权 | 是 |
| Content-Type | `application/json` |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 案件 ID，大于 0 |

**请求体（可选）：**

```json
{
  "force": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| force | boolean | 否 | 是否强制重新分析（即使已有报告），默认 false |

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "AI分析任务已提交",
  "data": {
    "case_id": 1,
    "task_id": 100,
    "ai_status": "PROCESSING",
    "case_status": "ANALYZING",
    "estimated_seconds": 30
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 任务已成功提交 |
| 404 | 案件不存在 |
| 409 | 案件正在分析中，不可重复触发（除非 force=true） |
| 500 | 任务提交失败 |

---

### 7.2 查询 AI 分析状态

**接口说明：** 查询指定案件的 AI 分析进度。前端可通过轮询此接口（建议间隔 3 秒）获取最新状态。

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/api/cases/{case_id}/analyze/status` |
| 鉴权 | 是 |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 案件 ID，大于 0 |

**请求示例：**

```
GET /api/cases/1/analyze/status
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "case_id": 1,
    "ai_status": "PROCESSING",
    "case_status": "ANALYZING",
    "current_step": "RAG",
    "progress": 60,
    "steps": [
      {"name": "INTENT", "label": "意图识别", "status": "SUCCESS", "latency_ms": 820},
      {"name": "EXTRACT", "label": "信息抽取", "status": "SUCCESS", "latency_ms": 1200},
      {"name": "COMPLETENESS", "label": "完整度判断", "status": "SUCCESS", "latency_ms": 530},
      {"name": "RAG", "label": "知识检索", "status": "RUNNING", "latency_ms": null},
      {"name": "REPORT", "label": "报告生成", "status": "PENDING", "latency_ms": null}
    ]
  }
}
```

**ai_status 枚举值：**

| 值 | 说明 |
|----|------|
| PENDING | 待处理 |
| PROCESSING | 处理中 |
| DONE | 处理完成 |
| FAILED | 处理失败 |

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 查询成功 |
| 404 | 案件不存在 |

---

### 7.3 获取最新分析报告

**接口说明：** 获取指定案件的最新版本 AI 分析报告。一个案件可能存在多版本报告（用户补充证据后 AI 重新分析生成新版），此接口只返回版本号最大的那一份。

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/api/report/{case_id}` |
| 鉴权 | 是 |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 案件 ID，大于 0 |

**请求示例：**

```
GET /api/report/1
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 8,
    "case_id": 1,
    "version": 2,
    "summary": "用户租赁合同到期后退房，房东以墙面损坏为由拒绝返还3000元押金。用户已提供退房视频证明墙面状态正常。",
    "risk_analysis": "风险等级：低风险。原因：用户已提供退房视频证明墙面正常，房东扣款理由不成立。",
    "legal_basis": "《民法典》第710条：承租人按照约定的方法或者租赁物的性质使用租赁物，致使租赁物受到损耗的，不承担赔偿责任。",
    "missing_evidence": "无。当前证据已较为充分。",
    "action_plan": "1.要求房东提供维修凭证 2.保存沟通记录 3.尝试协商 4.协商不成拨打12345投诉",
    "create_time": "2026-08-05 15:00:00"
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 查询成功 |
| 404 | 案件不存在，或该案件暂无分析报告 |
| 422 | case_id 非法 |

---

### 7.4 获取历史报告列表

**接口说明：** 获取指定案件的所有历史 AI 分析报告，按版本号倒序排列（最新版本在前）。用于查看报告版本演进、对比补充证据前后的分析效果。

| 项目 | 说明 |
|------|------|
| 方法 | GET |
| 路径 | `/api/reports/{case_id}` |
| 鉴权 | 是 |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 案件 ID，大于 0 |

**请求示例：**

```
GET /api/reports/1
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 8,
      "case_id": 1,
      "version": 2,
      "summary": "用户已提供退房视频证明墙面状态正常。",
      "risk_analysis": "风险等级：低风险。",
      "legal_basis": "《民法典》第710条...",
      "missing_evidence": "无。",
      "action_plan": "1.要求房东提供维修凭证 2.保存沟通记录 3.协商或投诉",
      "create_time": "2026-08-05 15:00:00"
    },
    {
      "id": 3,
      "case_id": 1,
      "version": 1,
      "summary": "用户租赁合同到期后退房，房东以墙面损坏为由拒绝返还3000元押金。",
      "risk_analysis": "风险等级：中风险。原因：房东存在扣款理由，但目前缺少维修费用证明。",
      "legal_basis": "《民法典》第710条；《民法典》第713条。",
      "missing_evidence": "退房验收记录、房东维修凭证。",
      "action_plan": "1.要求房东提供维修凭证 2.保存沟通记录 3.尝试协商",
      "create_time": "2026-08-05 14:35:00"
    }
  ]
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 查询成功（即使无报告也返回空数组） |
| 404 | 案件不存在 |
| 422 | case_id 非法 |

---

## 八、行动指南接口

### 8.1 生成行动指南

**接口说明：** 基于案件分析报告、已上传证据、风险等级，生成具体的行动方案。包含当前阶段判断、操作步骤、协商话术模板、投诉渠道等。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/cases/{case_id}/action-plan` |
| 鉴权 | 是 |
| Content-Type | `application/json` |

**Path 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | int | 是 | 案件 ID，大于 0 |

**请求体（可选）：**

```json
{
  "stage": "NEGOTIATION"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stage | string | 否 | 指定阶段：`NEGOTIATION`(协商) / `COMPLAINT`(投诉) / `LITIGATION`(法律途径)，未传则由系统判断 |

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "行动指南生成成功",
  "data": {
    "case_id": 1,
    "stage": "NEGOTIATION",
    "stage_label": "协商阶段",
    "steps": [
      {
        "step": 1,
        "title": "整理证据",
        "description": "确认已具备以下证据：合同、支付记录、聊天记录、退房视频",
        "checklist": [
          {"item": "租赁合同", "ready": true},
          {"item": "支付记录", "ready": true},
          {"item": "聊天记录", "ready": true},
          {"item": "退房视频", "ready": true}
        ]
      },
      {
        "step": 2,
        "title": "联系房东",
        "description": "使用以下话术与房东沟通",
        "template": "您好，关于押金返还问题，根据双方签订的租赁合同，目前房屋已完成交接，请提供相关维修依据，谢谢。"
      },
      {
        "step": 3,
        "title": "投诉渠道",
        "description": "协商不成可选择以下渠道",
        "channels": [
          {"name": "12345 市民热线", "type": "电话"},
          {"name": "住建局投诉", "type": "线上"},
          {"name": "消费者协会", "type": "电话"}
        ]
      },
      {
        "step": 4,
        "title": "法律途径",
        "description": "如投诉无果，可向法院提起诉讼",
        "notes": "建议咨询专业律师，准备起诉状及相关证据材料"
      }
    ],
    "attention": [
      "保留所有沟通记录截图",
      "不要在情绪激动时与房东发生冲突",
      "投诉时清晰陈述诉求和事实"
    ],
    "task_id": 105
  }
}
```

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 生成成功 |
| 404 | 案件不存在，或案件尚无分析报告 |
| 500 | AI 调用失败 |

---

## 九、合同风险检测接口

### 9.1 合同风险分析

**接口说明：** 对用户上传或粘贴的租房合同进行风险条款识别。支持两种输入方式：上传合同文件（PDF/Word/TXT）或直接粘贴合同文本。系统会自动切分条款、识别风险、给出修改建议。

| 项目 | 说明 |
|------|------|
| 方法 | POST |
| 路径 | `/api/contract/analyze` |
| 鉴权 | 是 |
| Content-Type | `multipart/form-data` 或 `application/json` |

**方式一：上传合同文件（form-data）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 合同文件，支持 PDF / Word / TXT，最大 20MB |
| user_id | int | 否 | 关联用户 ID（如需保存检测结果） |

**方式二：粘贴合同文本（json）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | 是 | 合同纯文本内容 |
| user_id | int | 否 | 关联用户 ID |

**请求示例（粘贴文本）：**

```json
{
  "content": "房屋租赁合同\n甲方（出租方）：张某\n乙方（承租方）：李某\n第一条 租期为2026年1月1日至2026年12月31日\n第二条 月租金3000元，押金3000元\n第三条 退租时房屋如有损坏，由乙方承担全部维修费用\n第四条 提前退租需支付2个月租金作为违约金",
  "user_id": 1
}
```

**响应示例（200）：**

```json
{
  "code": 200,
  "message": "合同风险分析完成",
  "data": {
    "overall_risk_level": "HIGH",
    "overall_risk_score": 75,
    "summary": "该合同存在多处不利于承租人的条款，建议修改后再签署。",
    "risk_items": [
      {
        "clause": "第三条 退租时房屋如有损坏，由乙方承担全部维修费用",
        "risk_type": "REPAIR",
        "risk_level": "HIGH",
        "problem": "维修责任完全由租客承担，未区分自然损耗和人为损坏",
        "suggestion": "按《民法典》第713条，出租人应履行维修义务。建议修改为：自然损耗由出租人负责维修，人为损坏由承租人承担维修费用。",
        "legal_basis": "《民法典》第713条"
      },
      {
        "clause": "第四条 提前退租需支付2个月租金作为违约金",
        "risk_type": "BREACH",
        "risk_level": "MEDIUM",
        "problem": "违约金比例偏高，可能超出实际损失",
        "suggestion": "建议协商降低至1个月租金，或约定按实际损失计算。",
        "legal_basis": "《民法典》第585条"
      },
      {
        "clause": "第二条 月租金3000元，押金3000元",
        "risk_type": "DEPOSIT",
        "risk_level": "MEDIUM",
        "problem": "未约定押金返还时间和条件",
        "suggestion": "建议增加条款：租赁期满或合同解除后7日内，在房屋无人为损坏的情况下，甲方应全额退还押金。",
        "legal_basis": "《民法典》第733条"
      }
    ],
    "missing_clauses": [
      {
        "clause": "维修责任条款",
        "suggestion": "应明确自然损耗与人为损坏的责任划分"
      },
      {
        "clause": "押金返还条款",
        "suggestion": "应明确押金返还时间和扣除条件"
      },
      {
        "clause": "房屋交付状态条款",
        "suggestion": "应记录入住时房屋现状，避免退房争议"
      }
    ],
    "task_id": 110
  }
}
```

**风险类型枚举：**

| 值 | 说明 |
|----|------|
| DEPOSIT | 押金条款风险 |
| REPAIR | 维修责任风险 |
| BREACH | 违约责任风险 |
| TERMINATION | 退租条件风险 |
| OTHER | 其他风险 |

**状态码：**

| 状态码 | 说明 |
|--------|------|
| 200 | 分析成功 |
| 400 | 合同内容过短（少于 50 字）或不支持识别 |
| 413 | 文件超过 20MB |
| 415 | 文件后缀不在允许列表内 |
| 500 | AI 调用失败 |

---

## 十、附录

### 10.1 枚举值参考

#### case_type（纠纷类型）

| 值 | 说明 |
|----|------|
| DEPOSIT | 押金纠纷 |
| RENT_CANCEL | 提前退租 |
| REPAIR | 维修责任 |
| CONTRACT | 合同问题 |

#### status（案件状态）

| 值 | 说明 | 触发条件 |
|----|------|---------|
| CREATED | 已创建 | 用户创建案件 |
| ANALYZING | 分析中 | AI 开始处理 |
| WAITING | 等待补充 | AI 追问，等待用户补充信息 |
| COMPLETED | 已完成 | 报告生成完毕 |

#### ai_status（AI 分析状态）

| 值 | 说明 |
|----|------|
| PENDING | 待处理 |
| PROCESSING | 处理中 |
| DONE | 处理完成 |
| FAILED | 处理失败 |

#### risk_level（风险等级）

| 值 | 说明 |
|----|------|
| LOW | 低风险 |
| MEDIUM | 中风险 |
| HIGH | 高风险 |

#### evidence_type（证据类型）

| 值 | 说明 | 典型文件 |
|----|------|---------|
| CONTRACT | 租赁合同 | PDF / 拍照件 |
| PAYMENT | 支付记录 | 转账截图 / 收据 |
| CHAT | 聊天记录 | 微信截图 |
| IMAGE | 房屋照片 | 入住 / 退房照片 |
| VIDEO | 视频 | 退房视频 |
| OTHER | 其他 | 维修报价单等 |

#### importance_level（证据重要程度）

| 值 | 说明 |
|----|------|
| HIGH | 重要（如合同、转账记录） |
| MEDIUM | 一般（如聊天记录） |
| LOW | 低价值（如无关照片） |

#### task_type（AI 任务类型）

| 值 | 说明 |
|----|------|
| INTENT | 意图识别 |
| EXTRACT | 信息抽取 |
| COMPLETENESS | 完整度判断 |
| RAG | 知识检索 |
| REPORT | 报告生成 |
| EVIDENCE_OCR | 证据 OCR 识别 |
| EVIDENCE_EXTRACT | 证据信息提取 |
| ACTION_PLAN | 行动方案生成 |

### 10.2 状态机说明

#### 案件状态流转

```
                  创建案件
                     │
                     ▼
                 ┌────────┐
                 │CREATED │
                 └────┬───┘
                      │ 触发 AI 分析
                      ▼
                 ┌──────────┐
        ┌──────│ANALYZING │──────┐
        │       └────┬─────┘      │
        │ AI 追问     │            │ AI 完成
        ▼            │            ▼
  ┌─────────┐        │      ┌──────────┐
  │ WAITING │────────┘      │COMPLETED │
  └────┬────┘ 用户补充证据   └──────────┘
       │ 重新触发分析
       └──────────► ANALYZING
```

#### AI 任务状态流转

```
PENDING ──► RUNNING ──► SUCCESS
                │
                └──► FAILED
```

### 10.3 错误码速查表

| 错误码 | HTTP 含义 | message 示例 |
|--------|----------|-------------|
| 200 | 成功 | success |
| 201 | 创建成功 | 案件创建成功 / 证据上传成功 |
| 400 | 参数错误 | 用户名或密码错误 / 合同内容过短 |
| 401 | 未授权 | 未授权，请先登录 |
| 404 | 未找到 | 案件不存在 / 用户不存在 / 该案件暂无分析报告 |
| 409 | 数据冲突 | 用户名已存在 / 案件正在分析中，不可重复触发 |
| 413 | 文件过大 | 文件不能超过 20MB |
| 415 | 不支持的媒体类型 | 仅支持 PDF、图片及 Word/TXT 文档 |
| 422 | 参数校验失败 | 请求参数校验失败 |
| 500 | 服务器错误 | 服务器内部错误 / AI 调用失败 |

---

