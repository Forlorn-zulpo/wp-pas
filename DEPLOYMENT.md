# 部署指南

## 环境要求

- Python 3.12+、Node.js 20+
- PostgreSQL 16+(需要 `pg_trgm` 扩展,迁移会自动启用)
- Redis 7+
- 一台能跑 systemd(或等价进程管理器)的 Linux 服务器;本文档不假设 Docker

## 1. 数据库与 Redis

```bash
sudo apt-get install -y postgresql redis-server
sudo -u postgres createuser --pwprompt app_user   # 生产环境换掉 dev 默认的 postgres/postgres
sudo -u postgres createdb -O app_user product_ops
```

## 2. 后端

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`,**生产环境必须修改**的几项:

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` / `ASYNC_DATABASE_URL` | 指向生产数据库,不要用 dev 默认的 postgres/postgres |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成 |
| `CREDENTIALS_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 生成。**丢失这个 key 等于丢失所有站点/供应商/AI 凭据,务必备份到密钥管理系统,不要只放在 .env 里** |
| `CORS_ORIGINS` | 改成生产前端的真实域名 |
| `S3_*` 或 `LOCAL_STORAGE_PATH` | 图片存储位置;生产建议切到真实 S3,见下方说明 |

迁移:

```bash
./venv/bin/alembic upgrade head
```

创建第一个管理员账号(只能成功一次,见 README):

```bash
curl -X POST https://your-api-domain/api/v1/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourcompany.com","password":"一个强密码","full_name":"管理员"}'
```

### systemd 服务(示例)

`/etc/systemd/system/product-ops-api.service`:

```ini
[Unit]
Description=Product Ops Admin API
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=app
WorkingDirectory=/opt/product-ops/backend
EnvironmentFile=/opt/product-ops/backend/.env
ExecStart=/opt/product-ops/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now product-ops-api
sudo systemctl status product-ops-api
```

把 uvicorn 放在 nginx/caddy 后面做 TLS termination;本项目本身不处理 HTTPS。

### 从 S3 兼容存储切换图片存储

当前默认把图片存在本地磁盘(`backend/app/services/storage.py` 的 `LocalDiskStorage`)。切到 S3 时:
1. 实现一个 `S3Storage(StorageService)`,用 `boto3`(已在依赖里)
2. 改 `get_storage_service()` 根据 `settings.S3_ENDPOINT_URL` 是否配置来决定返回哪个实现
3. 本地磁盘里已有的图片需要手动上传迁移到 S3,`assets` 表的 `storage_key` 字段不用改格式,只要 S3 实现用同样的 key 存取即可

## 3. 前端

```bash
cd frontend
npm install
npm run build        # 产出 dist/
```

把 `dist/` 丢给 nginx/caddy 当静态站点,或用任意静态托管(Netlify/Vercel/S3+CloudFront)。前端通过相对路径 `/api/v1/...` 调后端,生产环境需要反向代理把 `/api` 转发到后端服务(参考 `frontend/vite.config.ts` 里开发环境的代理配置思路)。

## 4. Celery(当前尚未接入,预留)

CSV 导入和发布任务目前是同步处理(见各自代码里的注释)。真要切到 Celery 异步执行时:

```bash
./venv/bin/celery -A app.celery_app worker --loglevel=info
```

(`app.celery_app` 还没创建——`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` 配置已经在 `.env.example` 里留好了,接入时只需要新建 Celery app 并把现有同步函数包装成 task。)

## 5. 上线前检查清单

- [ ] `.env` 里的 `JWT_SECRET_KEY`、`CREDENTIALS_ENCRYPTION_KEY` 已经是生产专用的随机值,不是仓库里的开发默认值
- [ ] 数据库用户不是 `postgres` 超级用户,权限最小化
- [ ] `GET /api/v1/health` 返回 `{"status":"ok","database":true,"redis":true}`
- [ ] 已经做过一次 `bootstrap-admin` 并能正常登录
- [ ] 站点凭据加密密钥已经备份(见上文 `CREDENTIALS_ENCRYPTION_KEY`)
- [ ] 数据库自动备份已配置(见 `BACKUP.md`)
