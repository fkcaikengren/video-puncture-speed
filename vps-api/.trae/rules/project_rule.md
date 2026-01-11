1. 项目使用的框架版本及依赖
- Python 版本：>= 3.12（推荐与 pyproject.toml 保持一致）
- 依赖管理与虚拟环境：使用 uv 管理虚拟环境与依赖
- Web 框架：FastAPI（>= 0.115.6）
- ASGI 服务器：uvicorn（>= 0.32.1）
- ORM 与数据库：
  - SQLAlchemy（>= 2.0.36） 封装在`app.core.database`模块中
  - asyncpg（>= 0.30.0）
  - PostgreSQL 作为主要数据库
  - alembic 进行数据库迁移
- 配置管理：pydantic-settings（>= 2.6.1），封装在`app.core.config`模块中
- 对象存储：使用 MinIO 作为对象存储服务， 封装在`app.core.storage`模块中

2. 测试框架的详细要求
- 测试框架：pytest（>= 8.0.0）
- 异步测试：pytest-asyncio（>= 0.23.5），asyncio_mode 使用 auto
- HTTP 客户端：httpx（>= 0.27.0）用于集成测试

3. 禁止使用的 API
- 禁止直接使用同步数据库驱动或阻塞式 IO 操作访问 PostgreSQL，应统一通过 SQLAlchemy 异步会话与 asyncpg 完成数据库访问
- 禁止在业务代码中直接使用 print 进行日志输出，应使用统一的日志封装（如 logging 或项目内 logger 工具）
- 禁止在代码中硬编码数据库密码、JWT 密钥、第三方服务密钥等敏感信息，必须通过环境变量或 pydantic-settings 配置管理
- 禁止使用SQLAlchemy1.x的语法，需要使用SQLAlchemy2.0语法，比如mapped_column等

4. 启动与测试命令（必须通过 uv 执行）
- 依赖安装与环境同步：
  - 首次或更新依赖：`uv sync`
- 应用启动（开发环境）：
  - 使用内置入口启动（推荐，使用配置中的端口）：`uv run python -m api.main`
  - 或使用 uvicorn 直接启动：`uv run uvicorn api.main:app --reload --port 8800`
- 运行测试：
  - 单元测试与覆盖率：`uv run pytest`
    - 运行单个测试文件，使用`uv run python -m pytest`, 例如： `uv run python -m pytest tests/core/test_storage.py`
    - pytest.ini 中已配置 `-v --cov=api --cov-report=term-missing` 和测试目录 tests
- 要求：
  - 所有与运行、测试、格式化相关的命令必须通过 uv（如 `uv run`、`uv sync`）执行
  - 禁止直接使用系统级 python、pip、pytest、uvicorn 等命令
