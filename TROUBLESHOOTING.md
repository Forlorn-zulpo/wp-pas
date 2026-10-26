# 故障排查

这份文档记录的都是开发过程中真实遇到并解决过的问题,不是泛泛而谈的 checklist。

## `GET /api/v1/health` 返回 `"redis": false`

Redis 没启动或 `REDIS_URL` 配错。`redis-server --daemonize yes` 起一下,或检查 `.env` 里的 `REDIS_URL` 是否指向正确的 host/port/db。CSV 导入和发布目前虽然是同步处理、不依赖 Redis,但这是为将来接 Celery 预留的检查项,现在报错不代表现有功能真的坏了——但如果 Redis 挂了说明基础设施有问题,应该当真报警处理。

## Alembic autogenerate 生成的迁移升级后,插入 PostgreSQL ENUM 的新值报错 `invalid input value for enum`

**这是本项目开发过程中最容易踩的坑**,原因:
1. Alembic 的 `--autogenerate` **检测不到** Python `enum.Enum` 新增的成员——它只对比表结构,不会发现你在 `app/models/enums.py` 里新加了一个值。必须手写迁移,用 `ALTER TYPE xxx ADD VALUE`。
2. `ALTER TYPE ... ADD VALUE` **不能跟使用这个新值的语句放在同一个事务里**,Alembic 默认每个迁移是一个事务,所以必须用 `with op.get_context().autocommit_block():` 包起来。
3. SQLAlchemy 的 `Enum` 列默认往数据库里存的是 Python 枚举成员的 **`.name`**(大写,比如 `BIND`),不是 `.value`(小写 `bind`)。第一次给 `auditaction` 加值时就因为手滑写成了小写,实际运行时 SQLAlchemy 发送的是大写 `BIND`,导致枚举值不匹配报错。

正确的写法模板(参考 `backend/migrations/versions/7f8096b9b95f_*.py`):

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE your_enum_name ADD VALUE IF NOT EXISTS 'YOUR_NEW_VALUE'")
```

加完新值后,**务必核对** Python 枚举的成员名和你写进 SQL 里的字符串完全一致(大小写敏感)。

## 测试里直接操作 `app.db.session.async_engine` 导致 Python 进程段错误(segfault)

`asyncpg` 的连接是绑定到创建它的事件循环的。测试框架(`fastapi.testclient.TestClient`)内部自己管理一个事件循环;如果你的测试代码额外用 `asyncio.run()` 再去操作同一个 `async_engine`,会产生跨事件循环操作同一批连接的情况,轻则报 `RuntimeError`,重则直接让解释器崩溃。

**规避方式**:
- 需要在测试里做额外的数据库校验时,开一个独立的、一次性的 engine(`create_async_engine(..., poolclass=NullPool)`),用完整个 `asyncio.run()` 包起来,绝不要碰应用自己的 `async_engine`
- 或者干脆用同步驱动(`psycopg2`)开一个独立连接做校验,最简单可靠(参见 `backend/tests/test_sites.py::test_credentials_are_actually_encrypted_in_the_database`)

## pytest-asyncio + `TestClient` 混用时各种 `RuntimeError: ... different loop`

本项目最终放弃了 `pytest-asyncio` + `httpx.AsyncClient` 的组合,改用同步的 `fastapi.testclient.TestClient`,所有测试函数都是普通 `def`,不是 `async def`。`TestClient` 内部自己管理 anyio 的事件循环,比手动协调 pytest-asyncio 的 fixture 作用域可靠得多。见 `backend/tests/conftest.py`。

## 商品搜索(`?search=`)在数据量大时很慢

`ILIKE '%keyword%'` 这种前导通配符的模糊搜索,普通 B-tree 索引用不上。已经通过 `pg_trgm` 扩展 + GIN 索引解决(迁移 `e88c9266da52`),2 万行数据下从 30ms 的全表扫描降到 1.3ms 的索引扫描。如果以后在别的字段上也要做模糊搜索,照这个模式加索引,不要指望 B-tree。

## `bcrypt`/`passlib` 报 `AttributeError: module 'bcrypt' has no attribute '__about__'`

新版 `bcrypt`(4.1+)移除了 `passlib` 依赖的内部属性。本项目已经在 `requirements.txt` 里锁定 `bcrypt==4.0.1`,正常 `pip install -r requirements.txt` 不会碰到这个问题;如果你手动升级过 `bcrypt`,降回 4.0.1 即可。

## Tailwind 样式不生效 / `npx tailwindcss init` 报错

本项目用的是 Tailwind v4,没有传统的 `tailwind.config.js` + `npx tailwindcss init` 流程,而是用 `@tailwindcss/vite` 插件(见 `frontend/vite.config.ts`)+ `frontend/src/index.css` 里的 `@import "tailwindcss";`。如果照着网上 v3 时代的教程走会卡在这一步。

## respx mock 测试报 "all routes must be called" 相关的 AssertionError

`respx.mock()` 默认 `assert_all_called=True`,如果你故意定义了一个"预期不会被调用"的路由(比如验证幂等性时断言 `create_route` 没被调用),必须显式传 `assert_all_called=False`,否则 respx 自己会在 `with` 块退出时报错。见 `backend/tests/test_publications.py`。
