

### 1. 数据库关系图 (ERD) 概览

主要分为四个核心板块：
- **认证与用户 (Auth)**
- **分类与视频管理 (Video Management)**
- **分析结果 (Analysis Data)**：核心业务数据。
- **对比报告 (Comparison & AI)**：存储对比逻辑与 AI 评价。

---

### 2. 表结构详细设计

#### 2.1 用户表 `users`
存储基本信息与权限等级。

| 字段名 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key | 用户唯一标识 (建议用 UUID) |
| `username` | `VARCHAR(50)` | Unique, Not Null | 登录账号 |
| `password_hash` | `VARCHAR(255)` | Not Null | 加密后的密码 |
| `role` | `VARCHAR(20)` | Not Null | 角色：`admin`, `user`, `viewer` |
| `created_at` | `TIMESTAMP` | Default Now() | 注册时间 |
| `updated_at` | `TIMESTAMP` | Default Now() | 更新时间 |

#### 2.2 视频分类表 `categories`
虽然目前只有一级分类，但独立成表方便后续扩展和筛选。

| 字段名 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | Primary Key | 分类 ID |
| `name` | `VARCHAR(50)` | Unique, Not Null | 分类名称（如：手背、肘窝） |
| `created_at` | `TIMESTAMP` | Default Now() | 创建时间 |

#### 2.3 视频主表 `videos`
存储上传的原始视频元数据。

| 字段名 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key | 视频唯一 ID |
| `user_id` | `UUID` | Foreign Key | 上传人 ID |
| `category_id` | `INT` | Foreign Key | 关联分类 ID |
| `title` | `VARCHAR(255)` | Not Null | 视频文件名/标题 |
| `raw_path` | `TEXT` | Not Null | 原始视频在 OSS/本地的存储路径 |
| `thumbnail_path`| `TEXT` | - | 视频缩略图路径 |
| `duration` | `DECIMAL(10,2)`| - | 视频总时长（秒） |
| `status` | `SMALLINT` | Not Null | 0:待处理, 1:处理中, 2:已完成, 3:失败 |
| `error_log` | `TEXT` | - | 如果失败，记录错误原因 |
| `created_at` | `TIMESTAMP` | Default Now() | 上传时间 |

#### 2.4 速度分析结果表 `analysis_results`
与 `videos` 表是一对一关系，存储分割模型计算出的核心指标。

| 字段名 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | `SERIAL` | Primary Key | 结果 ID |
| `video_id` | `UUID` | Unique, Foreign Key | 关联视频 ID (索引) |
| `marked_path` | `TEXT` | - | “标记视频”的存储路径 |
| `start_time` | `DECIMAL(10,3)`| - | 刺入开始时间点 (秒) |
| `end_time` | `DECIMAL(10,3)`| - | 刺入结束时间点 (秒) |
| `init_speed` | `DECIMAL(10,2)`| - | 初始速度 |
| `avg_speed` | `DECIMAL(10,2)`| - | 平均速度 |
| `curve_data` | `JSONB` | - | **核心：** 存储格式如 `[{"t":0.1, "v":2.5}, ...]` |
| `processed_at` | `TIMESTAMP` | - | 模型完成计算的时间 |

#### 2.5 对比记录/AI报告表 `comparison_reports`
用于记录用户进行的对比操作及 DeepSeek 返回的分析。

| 字段名 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key | 报告 ID |
| `video_a_id` | `UUID` | Foreign Key | 视频 A（通常是我的视频） |
| `video_b_id` | `UUID` | Foreign Key | 视频 B（通常是模范视频） |
| `user_id` | `UUID` | Foreign Key | 操作用户 ID |
| `ai_analysis` | `TEXT` | - | DeepSeek 返回的 Markdown 文本 |
| `created_at` | `TIMESTAMP` | Default Now() | 对比分析时间 |

---

### 3. 针对需求的架构师评估与优化建议

#### ① 关于 `curve_data` 的存储方案
*   **建议：** 使用 `JSONB` 格式。
*   **理由：** 速度曲线的点位数量取决于视频长度。`JSONB` 允许你在一次查询中直接把整条曲线拿给前端 ECharts 使用，避免了关联几百行“坐标点表”带来的查询开销。
*   **联动功能补充：** 虽然你划掉了“点击曲线跳转视频”，但如果未来要实现，JSONB 中的 `t` (timestamp) 字段可以直接映射到视频播放器的 `currentTime`。

#### ② 状态查询优化 (Dashboard)
*   **需求：** Dashboard 需要统计“总数、已完成、失败、处理中”。
*   **索引：** 必须在 `videos` 表的 `status` 字段上建立索引。
*   **查询：** 使用 `GROUP BY status` 即可一次性获取 Dashboard 右上角的所有统计数字。

#### ③ 性能评估：视频对比
*   **挑战：** 当对比两个视频时，前端需要同时拉取两份 `JSONB` 数据。
*   **方案：** 建议在查询 `video/compare` 接口时，后端一次性封装好 A 和 B 的曲线数据返回，减少 HTTP 请求次数，确保 ECharts 渲染同步。

#### ④ AI 分析 (DeepSeek) 的集成
*   **策略：** 调用 DeepSeek API 是耗时操作（通常 5-20s）。
*   **设计：** 在 `comparison_reports` 表中，可以增加一个 `status` 字段。用户点击“触发分析”后，前端显示 Loading，后端异步调用并存入该表，完成后通过 WebSocket 或轮询通知前端更新 UI。

#### ⑤ 索引建议
```sql
CREATE INDEX idx_video_status ON videos(status);
CREATE INDEX idx_video_user ON videos(user_id);
CREATE INDEX idx_video_category ON videos(category_id);
CREATE INDEX idx_analysis_video_id ON analysis_results(video_id);
```

### 4. 总结
该方案通过 `JSONB` 处理动态变化的曲线数据，通过 `UUID` 保证数据安全性与唯一性，并通过状态位设计满足 Dashboard 的监控需求。这种设计能够很好地支撑你描述的“视频上传 -> 模型处理 -> 结果展示 -> AI 对比”的完整生命周期。