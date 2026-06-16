# Fleetge

多主机 Docker fleet 管理控制台。聚合 Dockge、docker-socket-proxy、host-metrics exporter 三路数据源，提供统一只读监控 + Stack 基础操作。

## 架构

```
用户浏览器 ─HTTPS→ Fleetge Frontend (Vue 3)
                    ─REST→ Fleetge Backend (FastAPI)
                              ├─→ Dockge Socket.IO ─ stack 管理
                              ├─→ docker-socket-proxy ─ Docker 只读状态
                              └─→ host-metrics exporter ─ 主机指标
```

## 部署

### 1. 准备

```bash
# 生成必要密钥
python -c "import secrets; print(secrets.token_hex(32))"          # JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # CREDENTIALS_KEY

# 生成管理员密码 hash
pip install pwdlib[argon2]
python -c "from pwdlib import PasswordHash; print(PasswordHash.recommended().hash('your-admin-password'))"
```

### 2. 配置

```bash
cp .env.example .env           # 编辑 JWT_SECRET, CREDENTIALS_KEY, ADMIN_PASSWORD_HASH
cp hosts.yaml.example data/hosts.yaml   # 编辑各主机连接信息
```

**hosts.yaml** 结构：

```yaml
hosts:
  - host_id: oc-chicago
    display_name: OC Chicago
    dockge:
      url: https://dockge.1989009.xyz
      username: admin
      password: "dockge_password"
    docker_proxy:
      url: https://docker.1989009.xyz
      username: "monitor"
      password: "proxy_password"
    metrics:
      url: https://metrics.1989009.xyz
      username: "monitor"
      password: "metrics_password"
    sort_order: 1
    enabled: true
```

### 3. 部署

```bash
docker compose up -d
```

Fleetge 将在 `http://<host>:80` 可用。

### 4. 前置依赖

每台受管主机需要：

| 组件 | 说明 | 部署位置 |
|---|---|---|
| **Dockge** | Compose stack 管理 | 每台主机一个 |
| **docker-socket-proxy** | Docker 只读 HTTP API | 需增加 `INFO=1 VERSION=1 SYSTEM=1 IMAGES=1 EVENTS=0` |
| **host-metrics exporter** | 主机实时指标 (CPU/内存/磁盘) | 每台主机一个 |

Exporter 部署示例：

```bash
cd host-metrics-exporter
docker compose -f compose.example.yaml up -d
```

## 功能

- **主机总览**：在线状态、CPU/内存/磁盘利用率、Docker 版本
- **Stack 管理**：列表查看、启动/停止/重启/更新
- **容器状态**：列表、资源占用 (CPU/内存/网络/IO)
- **镜像更新检测**：自动对比 registry digest 判断可更新镜像
- **操作审计**：所有写操作记录时间戳和操作人
- **日志查看**：Stack 日志尾部查看（200–5000 行）

## 安全说明

- 后端凭据使用独立 `CREDENTIALS_KEY` (Fernet) 加密存储，不与 JWT 密钥共用
- 前端不保存任何远端凭据，仅持有 JWT token
- docker-socket-proxy 保持 `POST=0`，拒绝写入
- 登录 5 次失败后 IP 限速 15 分钟
- 写操作需前端二次确认 + 后端动作名白名单

## 路由

| 路径 | 说明 |
|---|---|
| `/login` | 登录 |
| `/` | 主机总览 |
| `/hosts/:hostId` | 主机详情 |
| `/updates` | 镜像更新 |
| `/audit` | 审计日志 |
| `/api/docs` | API 文档 (Swagger) |

## 开发

```bash
# 后端
cd backend
pip install -r requirements.txt
JWT_SECRET=dev CREDENTIALS_KEY=... ADMIN_PASSWORD_HASH=... uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

前端开发服务器自动代理 `/api` 到 `127.0.0.1:8000`。
