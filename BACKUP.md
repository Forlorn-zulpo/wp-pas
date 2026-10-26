# 备份与恢复

## 需要备份的东西

1. **PostgreSQL 数据库**——商品、站点、绑定、审核、发布记录、审计日志,一切结构化数据
2. **`CREDENTIALS_ENCRYPTION_KEY`**——没有这个 key,数据库里所有站点/供应商的加密凭据都是永久无法解密的乱码。这个 key **不在数据库里**,只在 `.env`,必须单独备份(建议放进密钥管理服务,而不是只放在服务器本地)
3. **图片资源**——本地磁盘模式下是 `backend/storage/assets/` 目录;切到 S3 后由 S3 自身的备份策略覆盖

## 数据库备份

```bash
# 每日全量备份,带时间戳
pg_dump -U app_user -h localhost -d product_ops -F c -f "backup_$(date +%Y%m%d_%H%M%S).dump"
```

建议用 cron 或 systemd timer 跑,保留最近 30 天 + 每月 1 份长期保留。备份文件要加密后再传到异地存储(S3/对象存储的另一个 bucket,和主库不同区域)。

## 恢复

```bash
# 恢复到一个全新的空库(永远不要直接恢复到生产库覆盖,先恢复到新库验证)
createdb -U app_user product_ops_restore_test
pg_restore -U app_user -d product_ops_restore_test backup_20260101_030000.dump

# 验证: 跑几条查询确认数据完整
psql -U app_user -d product_ops_restore_test -c "SELECT count(*) FROM products;"

# 确认无误后,才考虑切换生产库指向(需要停机窗口)
```

## 图片资源备份(本地磁盘模式)

```bash
rsync -av --delete /opt/product-ops/backend/storage/assets/ /backup/assets/
```

## 关于高风险操作

项目的删除操作默认是软删除/归档(`DELETE /products/{id}` 实际是把 `status` 改成 `archived`,不是真的删行;`assets` 删除是硬删除,因为图片文件本身没有审计/合规意义)。真正会丢数据的操作:
- 直接在数据库里 `DROP TABLE` / `TRUNCATE`
- 旋转/丢失 `CREDENTIALS_ENCRYPTION_KEY`(凭据永久不可恢复,只能让用户重新填一遍站点/供应商密钥)
- 覆盖 `.env` 却没保留旧的 `JWT_SECRET_KEY`(会导致所有人已签发的 token 立即失效,属于体验问题不是数据丢失,用户重新登录即可)

对前两种情况,操作前必须先手动确认有当天的数据库备份存在。
