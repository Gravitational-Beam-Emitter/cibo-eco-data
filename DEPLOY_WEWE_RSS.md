# 部署 WeWe RSS — 微信公众号文章定时抓取

## 前置条件
- Docker + Docker Compose
- 一个微信号（能用微信读书就行）

## 步骤 1：创建项目目录

```bash
mkdir -p ~/wewe-rss && cd ~/wewe-rss
```

## 步骤 2：写 docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
services:
  wewe-rss:
    image: cooderl/wewe-rss-sqlite:latest
    container_name: wewe-rss
    restart: always
    ports:
      - "4000:4000"
    environment:
      - DATABASE_TYPE=sqlite
      - AUTH_CODE=自行设置一个授权码
      - FEED_MODE=fulltext
      - CRON_EXPRESSION=35 8,20 * * *
    volumes:
      - ./data:/app/data
EOF
```

**环境变量说明**：

| 变量 | 说明 |
|---|---|
| `AUTH_CODE` | 登录授权码，设置后访问页面需要输入 |
| `FEED_MODE=fulltext` | 全文输出（不只是摘要） |
| `CRON_EXPRESSION=35 8,20 * * *` | 每天 08:35 和 20:35 自动更新 |

如需外网访问，加一行 `- SERVER_ORIGIN_URL=http://你的域名:4000`。

## 步骤 3：启动

```bash
docker compose up -d
```

## 步骤 4：扫码登录

1. 浏览器打开 `http://localhost:4000`
2. 输入 `AUTH_CODE` 里设的授权码
3. 点「登录」→ 弹出微信读书二维码
4. 手机微信扫一扫 → 确认登录

> **重要**：扫码时不要勾选「24小时后自动退出」。

## 步骤 5：订阅公众号

1. 在微信读书 App 里找到目标公众号 → 点进任意一篇文章
2. 点右上角「...」→「复制链接」
3. 回到 WeWe RSS 页面 → 粘贴链接 → 添加订阅
4. 重复以上，添加所有想监控的公众号

## 步骤 6：验证

页面会列出已订阅的公众号及其文章。RSS 地址格式：
```
http://localhost:4000/feeds/公众号名称.atom
```
可导入 Feedly、FreshRSS、Miniflux 等任意 RSS 阅读器。

---

## 常见问题

**Q: 登录态能维持多久？**
微信读书的登录态很稳定，通常能维持几个月。除非在微信读书 App 里主动退出。

**Q: 会被封号吗？**
不会。走的是微信读书网页版正常接口，行为等同于在网页上看文章。

**Q: 文章内容是全文吗？**
是，`FEED_MODE=fulltext` 开启全文输出。

**Q: 如何更换授权码？**
修改 `docker-compose.yml` 里的 `AUTH_CODE`，然后 `docker compose up -d --force-recreate`。

**Q: 如何备份数据？**
SQLite 数据库在 `./data` 目录下，直接备份这个目录即可。
