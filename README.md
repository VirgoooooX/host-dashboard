# Fleetge - Docker Fleet Console

Bilingual: [English](#english) | [简体中文](#简体中文)

---

## 简体中文

多主机 Docker 容器集群及 Compose Stack 统一运维控制台。

Fleetge 聚合了 `Dockge` / `fleetge-agent`、`docker-socket-proxy` 以及 `host-metrics` 数据源，在单容器内为您提供高效、低消耗的多主机状态只读监控、Compose Stack 启动/停止/重启/更新动作、容器资源占用（CPU/内存/网络/IO）实时看盘、镜像更新检测以及详细操作审计流水。

### 项目预览 / Previews

<p align="center">
  <img src="assets/login.png" width="48%" alt="Login" />
  <img src="assets/dashboard_preview1.png" width="48%" alt="Dashboard" />
</p>

<p align="center">
  <img src="assets/dashboard_preview2.png" width="48%" alt="Stack Details" />
  <img src="assets/dashboard_preview3.png" width="48%" alt="Metrics Monitor" />
</p>

<p align="center">
  <img src="assets/add%20compose.png" width="48%" alt="Add Compose" />
</p>

---

### 功能特性

*   **主机健康总览**：实时在线状态探测、CPU/内存/磁盘/网络指标大盘、容器运行数与 Docker 版本展示。
*   **多环境 Stack 管理**：支持 Stacks 的集中列示、生命周期操作（启动/重启/停止/删除/更新）、实时操作命令终端输出。
*   **三种 Stack 运行状态适配**：
    *   `已启动 (Active)`: 正常运行中的容器。
    *   `已退出 (Exited)`: 容器已执行 `Stop` 停止但仍保留在宿主机。
    *   `未启动 (Inactive)`: 容器已执行 `Down` 下线并被彻底清理。
*   **轻量级 Agent 架构 (`fleetge-agent`)**：可在受管主机上单容器替代 Dockge，提供独立日志流推送、Docker 系统清理 (`prune`)、及基于 SSH-like 的 Websocket 实时 Compose 命令流。
*   **容器资源精细监控**：单容器 CPU / 内存 / 网络接收与发送 / 磁盘 IO 读写频率秒级看盘与历史曲线。
*   **镜像更新智能检测**：无需第三方复杂组件，自动对比本地镜像与远端 Registry Digest 差异，精准发现待更新版本。
*   **安全可信与动作审计**：
    *   安全只读连接：原生适配 `docker-socket-proxy` 的只读限制（`POST=0`）。
    *   安全存储：受管主机的 API 凭据及 Token 均使用独立 `CREDENTIALS_KEY`（基于 Fernet 加密）安全落库。
    *   安全登录：内置登录尝试次数限制防暴力破解。
    *   写操作审计：所有通过控制台发起的 Stack 操作指令和系统清理动作均会计入审计日志，可精确追踪操作 IP、时间、人及执行结果。

---

### 系统架构

```
用户浏览器 ─HTTPS→ Fleetge 单容器控制台 (FastAPI + Vue 3)
                    ├─→ 受管主机 A: (Dockge API ─ Stack 读写控制)
                    │             (docker-socket-proxy ─ 只读 API)
                    │             (host-metrics exporter ─ 性能指标)
                    │
                    └─→ 受管主机 B: (fleetge-agent ─ 替代 Dockge + 监控融合)
```

---

### 部署与配置

#### 1. 密钥准备

在部署控制台前，您需要生成必要的加密密钥：

```bash
# 1. 生成 JWT 签名密钥 (JWT_SECRET)
python -c "import secrets; print(secrets.token_hex(32))"

# 2. 生成远端密码解密密钥 (CREDENTIALS_KEY)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. 生成管理员登录密码的 Argon2 密码 Hash (ADMIN_PASSWORD_HASH)
pip install pwdlib[argon2]
python -c "from pwdlib import PasswordHash; print(PasswordHash.recommended().hash('your-admin-password'))"
```

#### 2. 配置环境变量

复制 `.env.example` 并填入第一步中生成的密钥信息：

```bash
cp .env.example .env
```

> **注意：** `ADMIN_PASSWORD_HASH` 是 Argon2 字符串，其中包含 `$` 字符。在 `.env` 中**必须使用单引号**包裹该变量，否则 Docker Compose 可能会将 `$argon2id` 等解析为环境变量插值：
> ```env
> ADMIN_PASSWORD_HASH='$argon2id$v=19$m=65536,t=3,p=4$...'
> ```

#### 3. 配置主机列表 (`hosts.yaml`)

创建并编辑主机配置文件 `data/hosts.yaml`：

```bash
cp hosts.yaml.example data/hosts.yaml
```

**配置结构示例 (Dockge 托管主机)：**

```yaml
hosts:
  - host_id: ch-chicago
    display_name: Chicago Prod Server
    dockge:
      url: https://dockge.domain.com
      username: admin
      password: "dockge_password"
    docker_proxy:
      url: https://docker.domain.com
      username: "monitor"
      password: "proxy_password"
    metrics:
      url: https://metrics.domain.com
      username: "monitor"
      password: "metrics_password"
    sort_order: 1
    enabled: true
```

**配置结构示例 (Agent 托管主机)：**

如果使用更轻量、安全的 `fleetge-agent` 替代模式，配置极为精简：

```yaml
hosts:
  - host_id: hk-agent
    display_name: HK Agent Server
    agent_url: http://hk-agent-ip:8080
    agent_token: "your_agent_secret_token"
    sort_order: 2
    enabled: true
```

#### 4. 受管主机端组件部署

根据您的受管主机模式，在受管主机上部署对应的辅助程序：

##### 模式 A：使用 Fleetge Agent 托管 (推荐)

在您的被监控主机上，创建并运行如下 `docker-compose.agent.yml`：

```yaml
services:
  agent:
    image: ghcr.io/virgoooox/fleetge-agent:latest
    container_name: fleetge-agent
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - AGENT_TOKEN=your_agent_secret_token # 与主控台 hosts.yaml 配置的 token 保持一致
      - STACKS_BASE_DIR=/opt/stacks         # Stack 项目的存放目录
      - DISK_PATHS=/                        # 性能指标要监控的磁盘路径（支持逗号分隔多个路径）
      - COLLECT_INTERVAL=5                  # 指标数据采集间隔 (秒)
      - AGENT_LOG_LEVEL=info                # 运行日志级别 (可选: info / warning / error)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /opt/stacks:/opt/stacks
```

##### 模式 B：Dockge 官方套件模式

需要在受管主机上运行以下三个原生组件：
1.  **Dockge**: 提供底层的 compose 操作和 websocket 命令桥接。
2.  **docker-socket-proxy**: 暴露受保护的只读 API，启动环境变量必须包含 `INFO=1 VERSION=1 SYSTEM=1 IMAGES=1 EVENTS=0`。
3.  **host-metrics exporter**: 我们项目提供的极简物理主机资源指标收集器。
    *   部署方式：
        ```bash
        cd host-metrics-exporter
        docker compose -f compose.example.yaml up -d
        ```

#### 5. 启动控制台

```bash
docker compose up -d
```

完成后在浏览器访问 `http://<ip>:80` 即可登入。

---

## English

A multi-host Docker fleet and Compose Stack management console.

Fleetge consolidates data sources from `Dockge` / `fleetge-agent`, `docker-socket-proxy`, and `host-metrics exporter` to deliver a lightweight, real-time read-only status dashboard, container resource monitoring, image update notification, stack actions, and audit logs.

### Feature Highlights

*   **Host Health Overview**: Live ping status, real-time CPU/memory/disk network stats, running containers, and Docker versions.
*   **Multi-Environment Stack Management**: Centralized stack listing, lifecycle operations (Start, Stop, Restart, Update, Delete), and live SSE stream command terminals.
*   **Three Stack Running States**:
    *   `Active`: Containers are running normally.
    *   `Exited`: Containers are stopped via `Stop` but kept on the host.
    *   `Inactive`: Containers are removed via `Down`, marking the stack inactive.
*   **Lightweight Agent (`fleetge-agent`)**: A single-container replacement for Dockge on remote hosts, offering WebSocket-based compose actions, logs aggregation, and system prune operations.
*   **Granular Container Monitoring**: Container CPU, memory, network transmit/receive, and disk I/O metrics read at a 1-second cadence.
*   **Smart Image Update Detection**: Compares local image digests with remote registries directly to pinpoint updatable stacks without installing heavy third-party daemons.
*   **Secure & Audited**:
    *   Restricted API: Out-of-the-box support for `docker-socket-proxy` in read-only mode (`POST=0`).
    *   Credential Encryption: Remote host keys and passwords are encrypted in transit and database using a dedicated Fernet keyset (`CREDENTIALS_KEY`).
    *   Audit Logging: Tracks all write operations (actions, host names, IP addresses, usernames, execution results, and timestamps) for maximum compliance.

---

### Quick Start & Installation

#### 1. Generate Encryption Keys

Generate the security tokens and credential keys beforehand:

```bash
# 1. Generate JWT signing secret
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Generate Fernet key for database credentials
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. Hash the admin password using Argon2
pip install pwdlib[argon2]
python -c "from pwdlib import PasswordHash; print(PasswordHash.recommended().hash('your-admin-password'))"
```

#### 2. Environment Configuration

Copy the example environment file and insert your keys:

```bash
cp .env.example .env
```

> **IMPORTANT:** Ensure `ADMIN_PASSWORD_HASH` is enclosed in single quotes `'` inside the `.env` file to prevent shell and compose parser interpolation of `$` signs.
> ```env
> ADMIN_PASSWORD_HASH='$argon2id$v=19$m=65536,t=3,p=4$...'
> ```

#### 3. Set Up Hosts (`hosts.yaml`)

Initialize your cluster database config by making a copy of `hosts.yaml.example`:

```bash
cp hosts.yaml.example data/hosts.yaml
```

**Host Configuration Example (Dockge Managed Host):**

```yaml
hosts:
  - host_id: oc-chicago
    display_name: Chicago Prod Server
    dockge:
      url: https://dockge.domain.com
      username: admin
      password: "dockge_password"
    docker_proxy:
      url: https://docker.domain.com
      username: "monitor"
      password: "proxy_password"
    metrics:
      url: https://metrics.domain.com
      username: "monitor"
      password: "metrics_password"
    sort_order: 1
    enabled: true
```

**Host Configuration Example (Agent Managed Host):**

```yaml
hosts:
  - host_id: hk-agent
    display_name: HK Agent Server
    agent_url: http://hk-agent-ip:8080
    agent_token: "your_agent_secret_token"
    sort_order: 2
    enabled: true
```

#### 4. Run Agent Components on Remote Hosts

Depending on your architecture, choose one of the options below to run on your monitored hosts:

##### Option A: Using Fleetge Agent (Recommended)

Save the following as `docker-compose.agent.yml` and deploy it on your remote machine:

```yaml
services:
  agent:
    image: ghcr.io/virgoooox/fleetge-agent:latest
    container_name: fleetge-agent
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - AGENT_TOKEN=your_agent_secret_token
      - STACKS_BASE_DIR=/opt/stacks
      - DISK_PATHS=/
      - COLLECT_INTERVAL=5
      - AGENT_LOG_LEVEL=info # Optional log level: info / warning / error
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /opt/stacks:/opt/stacks
```

##### Option B: Standard Dockge Setup

Run the official `Dockge`, a configured `docker-socket-proxy` (ensure `INFO=1 VERSION=1 SYSTEM=1 IMAGES=1 EVENTS=0` is set), and our `host-metrics exporter`.
*   Deploy metrics exporter:
    ```bash
    cd host-metrics-exporter
    docker compose -f compose.example.yaml up -d
    ```

#### 5. Launch the Console

```bash
docker compose up -d
```

Visit the dashboard at `http://<your-host-ip>:80`.

---

## Local Development

To run the project locally for testing or development:

```bash
# Backend setup
cd backend
pip install -r requirements.txt
JWT_SECRET=dev CREDENTIALS_KEY=your_key ADMIN_PASSWORD_HASH=your_hash uvicorn app.main:app --reload

# Frontend setup
cd frontend
npm install
npm run dev
```

---

## License

MIT License.
