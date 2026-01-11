
## 接口通用规范（可执行）

- **基础路径**：`/api/v1`
- **认证方式**：Header 携带 `Authorization: Bearer {token}`
- **HTTP 方法**：仅使用 `GET` 和 `POST`
  - 查询类接口使用 `GET`
  - 新增/修改/删除类接口使用 `POST`
- **资源 ID 传参**：不放路径参数，统一放在 Query 中（例如 `?id={uuid}`、`?user_id={uuid}`）
- **命名风格**：Query 参数与 JSON 字段统一使用 `snake_case`
- **时间格式**：响应中的时间字段统一为 Unix 时间戳（毫秒，UTC），例如 `1767617550000`

### 响应包裹

所有接口均使用如下外层结构：

```json
{ "code": 200, "errMsg": "", "data": {} }
```

- `code=200` 表示业务成功
- 业务失败使用非 200（建议：400/401/403/404/409/500），同时 `errMsg` 给出可读错误信息

### 分页规范

- 请求：`page`（从 1 开始）、`page_size`
- 响应：

```json
{
  "code": 200,
  "errMsg": "success",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 1. 认证模块（Auth）

### 1.1 用户登录

- **接口**：`POST /auth/login`
- **Content-Type**：`application/json`
- **请求体**：

```json
{ "username": "admin", "password": "password123" }
```

- **返回 data**：

```json
{
  "token": "jwt_token",
  "user": {
    "id": "uuid",
    "username": "admin",
    "role": "admin"
  }
}
```

---

## 2. Dashboard 模块

### 2.1 获取统计概览

- **接口**：`GET /dashboard/stats`
- **Query**：
  - `scope`：`me|all`（默认 `me`；非 admin 传 `all` 也按 `me` 处理）
- **返回 data**：

```json
{
  "total": 100,
  "completed": 60,
  "pending": 20,
  "failed": 5,
  "processing": 15
}
```

### 2.2 获取待处理视频时间线

- **接口**：`GET /dashboard/pending-videos`
- **说明**：仅包含 `status=0(pending)` 的视频，按 `created_at` 日期分组，日期倒序
- **返回 data**：

```json
[
  {
    "date": "2026-01-05",
    "list": [
      {
        "id": "uuid",
        "title": "video_01.mp4",
        "thumbnail_url": "https://..."
      }
    ]
  }
]
```

---

## 3. 视频管理模块（Video）

### 3.1 视频库列表查询（分页）

- **接口**：`GET /videos`
- **Query**：
  - `keyword`：标题搜索（可选）
  - `category_id`：分类筛选（可选）
  - `status`：状态码筛选（可选，0/1/2/3）
  - `page`、`page_size`
- **返回 data（分页）**：

```json
{
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "category_id": 1,
      "title": "xxx",
      "duration": 1.23,
      "status": 2,
      "thumbnail_url": "https://...",
      "created_at": 1767617550000
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 3.2 视频详情

- **接口**：`GET /videos/detail`
- **Query**：`id`
- **返回 data**：

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "category_id": 1,
  "title": "xxx",
  "raw_url": "https://...",
  "thumbnail_url": "https://...",
  "duration": 1.23,
  "status": 2,
  "error_log": null,
  "created_at": 1767617550000
}
```

### 3.3 上传视频

- **接口**：`POST /videos/upload`
- **Content-Type**：`multipart/form-data`
- **Form**：
  - `file`：视频文件（必填）
  - `title`：标题（可选；缺省取文件名）
  - `category_id`：分类 ID（可选）
- **说明**：创建视频记录，初始 `status=0(pending)`；`raw_path` 存储对象 Key，响应中返回可访问的 `raw_url`
- **返回 data**：

```json
{
  "id": "uuid",
  "status": 0,
  "raw_url": "https://...",
  "thumbnail_url": null,
  "created_at": 1767617550000
}
```

### 3.4 删除视频（物理删除）

- **接口**：`POST /videos/delete`
- **Query**：`id`
- **删除策略（避免级联删除报错）**：
  - 先删除 `comparison_reports` 中 `video_a_id=id` 或 `video_b_id=id` 的记录
  - 再删除 `analysis_results` 中 `video_id=id` 的记录
  - 最后删除 `videos` 记录
  - 若删除过程中仍存在外键约束冲突，返回 `409` 并给出 `errMsg`
- **返回 data**：

```json
{ "deleted": true }
```

---

## 4. 速度分析模块（Analysis）

### 4.1 获取视频分析核心数据

- **接口**：`GET /videos/analysis`
- **Query**：`id`
- **说明**：若尚未产生分析结果，返回 `status` 与空的 `analysis`，前端据此展示“处理中/未完成/失败”
- **返回 data**：

```json
{
  "video": {
    "id": "uuid",
    "title": "xxx",
    "raw_url": "https://...",
    "status": 2,
    "error_log": null
  },
  "analysis": {
    "marked_url": "https://...",
    "metrics": {
      "start_time": 1.25,
      "end_time": 3.45,
      "init_speed": 12.5,
      "avg_speed": 10.2
    },
    "curve_data": [
      { "t": 0.0, "v": 0.0 },
      { "t": 0.1, "v": 2.5 }
    ],
    "processed_at": 1767617550000
  }
}
```

---

## 5. 对比与 AI 模块（Comparison）

### 5.1 获取对比候选视频列表（分页）

- **接口**：`GET /videos/candidates`
- **Query**：
  - `category_id`（可选）
  - `keyword`（可选）
  - `page`、`page_size`
- **筛选规则**：默认仅返回 `status=2(completed)` 且已存在分析结果（`analysis_results`）的视频
- **返回 data（分页）**：同 `GET /videos` 的分页结构，`items` 字段至少包含 `id/title/thumbnail_url`

### 5.2 触发 AI 深度分析（含幂等复用）

- **接口**：`POST /comparisons/ai-analyze`
- **Content-Type**：`application/json`
- **请求体**：

```json
{ "video_a_id": "uuid", "video_b_id": "uuid" }
```

- **幂等/复用策略**：
  - 以“当前登录用户”为范围查找历史报告
  - 将 `(video_a_id, video_b_id)` 视为无序对，后端查询 `(a,b)` 或 `(b,a)` 任意命中即复用
  - 命中则直接返回历史 `ai_analysis`，未命中才调用 AI 并写入 `comparison_reports`
- **返回 data**：

```json
{
  "id": "uuid",
  "video_a_id": "uuid",
  "video_b_id": "uuid",
  "ai_analysis": "# Markdown...",
  "created_at": 1767617550000
}
```

### 5.3 获取历史对比报告

- **接口**：`GET /comparisons/report`
- **Query**：`video_a_id`、`video_b_id`
- **说明**：同样按“当前用户 + 无序对”规则命中，未命中返回 `404`

---

## 6. 管理员模块（Admin Only）

### 6.1 用户列表获取（分页）

- **接口**：`GET /admin/users`
- **权限**：仅 `role=admin`
- **Query**：
  - `keyword`（可选，按用户名模糊匹配）
  - `role`（可选）
  - `page`、`page_size`
- **返回 data（分页）**：

```json
{
  "items": [
    {
      "id": "uuid",
      "username": "admin",
      "role": "admin",
      "created_at": 1767617550000
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

### 6.2 添加新用户

- **接口**：`POST /admin/users/create`
- **Content-Type**：`application/json`
- **请求体**：

```json
{ "username": "xxx", "password": "xxx", "role": "user" }
```

- **返回 data**：

```json
{ "id": "uuid" }
```

### 6.3 修改用户角色

- **接口**：`POST /admin/users/set-role`
- **Query**：`user_id`
- **Content-Type**：`application/json`
- **请求体**：

```json
{ "role": "admin" }
```

---

## 7. 分类（Category）

### 7.1 获取全部分类

- **接口**：`GET /categories`
- **返回 data**：

```json
[
  { "id": 1, "name": "xxx" }
]
```

---

## API 映射总结表

| 页面 | 接口 | 核心逻辑 |
| :--- | :--- | :--- |
| 登录页 | `POST /auth/login` | 返回 Token 与用户信息 |
| Dashboard | `GET /dashboard/stats` | 汇总状态统计 |
| Dashboard | `GET /dashboard/pending-videos` | 待处理时间线 |
| 视频库 | `GET /videos` | 分页搜索与筛选 |
| 视频库 | `GET /videos/detail?id=...` | 详情查询 |
| 视频库 | `POST /videos/upload` | 上传并创建记录 |
| 视频库 | `POST /videos/delete?id=...` | 删除并规避级联冲突 |
| 分析页 | `GET /videos/analysis?id=...` | 查询曲线与指标 |
| 对比页 | `GET /videos/candidates` | 可对比视频候选 |
| 对比页 | `POST /comparisons/ai-analyze` | 触发 AI（可复用） |
| 对比页 | `GET /comparisons/report` | 获取历史报告 |
| 用户管理 | `GET /admin/users` | 管理员分页列表 |
| 用户管理 | `POST /admin/users/create` | 创建用户 |
| 用户管理 | `POST /admin/users/set-role?user_id=...` | 设置角色 |
