# 导入对话：设计 Dockge 管理看板

来源线程：`019ec640-e025-73c0-aeb9-181cfb8e4beb`

原线程标题：设计 Dockge 管理看板

导入目标：把旧对话中已经收敛的产品方向、技术架构、安全约束和实现计划沉淀到当前 `Host Dashboard` 项目，后续开发以本文档为上下文。

## 原始需求

用户最初目标：

- 自己开发一个多终端 / 多主机 Dockge 管理看板。
- 能看到哪个容器或 service 有镜像更新。
- 能按主机展开 / 折叠查看 stacks、services、containers。
- 更像中文运维控制台，而不是重新做一个完整 Dockge UI。

最早讨论中的产品形态：

- 首页按主机分组，例如 VPS、NAS、iStoreOS 等。
- 每台主机一行摘要，展开后显示 stack，再展开到 service / container。
- 顶部汇总在线主机数、运行容器数、可更新服务数、异常服务数、最近检查时间。
- 更新状态使用清晰标签：`最新`、`可更新`、`检查失败`、`私有仓库需认证`。
- 支持筛选：只看可更新、只看异常、按镜像仓库 / 主机 / stack 搜索。
- 早期设想过只做观察型看板，后续讨论后 v1 范围扩大到支持有限 stack 操作。

## 最终收敛方向

做一个中文多主机 Docker / Dockge 管理看板。

第一版不 fork Dockge，不改 Dockge，不从零替代 Compose 执行器。Dashboard 后端统一聚合三个数据源：

- `Dockge Socket.IO`：负责 Compose stack 的读取和操作。
- `docker-socket-proxy`：负责 Docker 只读状态、容器、镜像、磁盘占用、stats。
- `host-metrics-exporter`：负责主机实时 CPU、内存、磁盘、load、uptime。

浏览器只访问 Dashboard 前后端，不直接访问 Dockge、docker-socket-proxy 或 host-metrics-exporter。

```text
Browser
  -> HTTPS
Dashboard Frontend
  -> REST / SSE / WebSocket
Dashboard Backend
  -> Dockge Socket.IO
  -> docker-socket-proxy
  -> host-metrics-exporter
  -> registry APIs
```

## 关键决策

### 不做 Komodo fork

讨论过 Komodo 中文化。Komodo 产品方向合适，但 UI 没有现成 i18n 结构，全量中文化维护成本较高。用户认为 Komodo 功能过多，当前需求更轻量，因此放弃 fork Komodo。

### 不做 Dockge fork 作为 v1 前提

讨论过 fork Dockge、自建稳定镜像、增加 dashboard API、agent token、事件白名单等。后来结合当前环境做了修正：

- 当前多台 Dockge 已经通过 Lucky / HTTPS 反代公网可访问。
- v1 先不大改远端 agent 架构。
- 先做独立 Dashboard 后端适配现有 Dockge Socket.IO。
- 等第一版跑通后，再决定是否 fork Dockge 加稳定 API / token / 白名单。

### Dockge 只负责 stack 视角

Dockge 可以提供：

- stack 列表
- stack 详情
- service 状态
- stack start / stop / restart / update
- stack 日志

Dockge 不适合作为完整主机监控源。它不是 observability agent，无法可靠提供主机整体 CPU、内存、磁盘、load 等实时指标。

### docker-socket-proxy 负责 Docker 只读状态

已有多台机器为 Homepage 部署过 docker-socket-proxy，可复用为 Dashboard 状态采集源。

v1 保持只读，不开启 Docker 写操作：

```env
POST=0
INFO=1
VERSION=1
SYSTEM=1
CONTAINERS=1
IMAGES=1
EVENTS=0
```

说明：

- `EVENTS=1` 曾被列入草案，但 review 后建议 v1 默认关闭。
- 第一版前端 10s 轮询即可，不需要公网实时 Docker events 面。

### host-metrics-exporter 是 v1 必需项

用户明确要求主机实时状态不能从 Docker API 硬推导，而是通过单独 exporter 获取。

exporter 职责：

- 只读 HTTP 服务。
- 不挂 Docker socket。
- 不执行任意命令。
- 返回主机 CPU、内存、磁盘、load、uptime。
- 支持配置监控磁盘路径。
- exporter 离线时，主机显示“指标异常”，但不影响 Dockge stack 操作和 Docker 状态读取。

当前项目已经有 `host-metrics-exporter` 目录，说明实现已从该模块开始。

## v1 功能边界

### 主机总览

- 主机在线 / 离线。
- CPU 使用率。
- 内存使用率。
- 磁盘使用率。
- load average。
- uptime。
- Docker 版本、API 版本、系统架构。
- Docker root dir。
- 容器数量：running / stopped / total。
- 镜像数量。
- Docker 占用空间：images / containers / volumes / build cache。

### Stack 管理

- 按主机折叠 / 展开。
- 每台主机下显示 Dockge stacks。
- 显示 stack 状态、compose 文件名、service 数、运行 / 退出服务数。
- 支持 `start`、`stop`、`restart`、`update`。
- v1 不支持删除 stack。
- v1 不支持编辑 compose。
- v1 不支持任意终端。
- 不把 Dockge 的广义 CRUD 暴露到 Dashboard。

### 容器 / 服务状态

- 从 docker-socket-proxy 获取容器列表和 inspect。
- 使用 Compose labels 关联 stack / service：
  - `com.docker.compose.project`
  - `com.docker.compose.service`
  - `com.docker.compose.config-hash`
  - `com.docker.compose.project.working_dir`
  - `com.docker.compose.project.config_files`
- 展示容器状态、镜像、端口、创建时间、CPU、内存、网络、IO。

### 日志

review 后建议 v1 不急着做 SSE 长连接日志。

推荐 v1：

- 先做尾部 200 行日志 + 手动刷新。
- 日志优先走 docker-socket-proxy 的 container logs。
- Dockge 日志作为 stack 聚合日志来源或后备。

SSE / 实时日志放到 v1.5，并补连接上限、超时、取消和鉴权。

### 镜像更新提示

- 从容器 image 和 compose service image 提取镜像引用。
- 查询 registry manifest digest。
- 对比本地 image digest。
- 显示：
  - `up_to_date`
  - `update_available`
  - `unknown`
  - `private_registry_auth_required`
  - `registry_error`
  - `local_image_missing`

重要修正：

- 不能认为“只有 `latest` 可判断，其他可变 tag 无法判断”。
- 大多数 tag 都可变，只要能取到本地 digest 和远端 manifest digest，就可以判断。
- 真正无法判断的是本地缺 RepoDigest、私有 registry 无认证、多架构 digest 映射失败等情况。

## 后端设计

推荐技术栈：

- Python FastAPI。
- `httpx + asyncio` 拉取 docker-socket-proxy、host-metrics-exporter、registry。
- `python-socketio AsyncClient` 连接 Dockge Socket.IO。
- SQLite 起步。
- 后续可迁移 Postgres。

后端维护每台主机配置：

- `hostId`
- `displayName`
- `dockgeUrl`
- `dockgeUsername`
- `dockgePasswordEncrypted`
- `dockerProxyUrl`
- `dockerProxyAuthEncrypted`
- `metricsUrl`
- `metricsAuthEncrypted`
- `enabled`
- `created_at`
- `updated_at`
- `last_seen`
- `status`
- `error_message`

后端职责：

- 加密保存 Dockge、docker proxy、metrics 凭据。
- 对前端提供统一 REST API。
- 维护 Dockge Socket.IO 连接池。
- 定时轮询 docker-socket-proxy 和 host-metrics-exporter。
- 缓存快照，避免前端频繁打远端。
- 写操作审计日志。
- 对 Dockge 写操作做白名单。

缓存建议：

- `metrics`：3-5 秒。
- `containers/stacks`：10 秒。
- `update-checks`：6 小时。

SQLite 注意：

- v1 可用 SQLite。
- 启用 WAL。
- 明确单进程部署。
- 如果登录限速仍用内存，要明确 `uvicorn --workers 1`。
- 更稳妥的限速可用 SQLite 记录失败登录窗口。

## API 草案

```text
GET  /api/hosts
GET  /api/hosts/:hostId/stacks
GET  /api/hosts/:hostId/containers
GET  /api/hosts/:hostId/docker
GET  /api/hosts/:hostId/metrics

POST /api/hosts/:hostId/stacks/:stack/start
POST /api/hosts/:hostId/stacks/:stack/stop
POST /api/hosts/:hostId/stacks/:stack/restart
POST /api/hosts/:hostId/stacks/:stack/update

POST /api/update-checks/run
GET  /api/update-checks
GET  /api/audit-logs
```

## 安全约束

Dashboard 是唯一用户入口。

前端不保存、也不直接接触：

- Dockge 凭据。
- docker-socket-proxy 凭据。
- host-metrics-exporter 凭据。

凭据加密：

- 不要用 `JWT_SECRET[:32]` 派生 Fernet key。
- 单独配置 `CREDENTIALS_KEY`。
- `CREDENTIALS_KEY` 用于凭据加密。
- `JWT_SECRET` 只用于 JWT。
- 启动时校验 key 格式。

Basic Auth 说明：

- Basic Auth 的 base64 不是加密。
- 数据库存储时应保存 Fernet 加密后的结构化凭据，例如 `{ username, password }` 或完整 Authorization header 密文。

登录：

- 单管理员 v1 可接受。
- 管理员来自环境变量初始化。
- 推荐 `.env` 放 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD_HASH`。
- 密码 hash 用 argon2id。
- 数据库已有管理员后，不再覆盖。
- 提供命令生成 hash，例如 `python -m app.security hash-password`。

写操作：

- 只允许 stack `start` / `stop` / `restart` / `update`。
- 后端不接受任意 `action` 字符串再拼接到 Dockge Socket.IO。
- 每次写操作写审计日志。
- 前端必须二次确认。

公网风险：

- 当前每台 Dockge 已经通过 Lucky / HTTPS 暴露公网。
- Dockge 挂 Docker socket，属于高权限入口。
- 第一版重点是加固 Lucky、Dashboard 登录、凭据存储和操作白名单。
- 后续如果风险不可接受，再演进到远端 agent 主动出站连接中心的架构。

## 前端设计要求

页面：

- `/login`
- `/` 主机总览
- `/hosts/:hostId` 主机详情
- `/updates` 镜像更新
- `/audit` 操作记录
- `/settings` 主机配置

风格：

- 中文优先。
- 运维控制台风格。
- 信息密度高。
- 不做营销首页。
- 不做装饰性 hero。
- 主机、stack、container 信息要适合扫描和反复操作。

首页：

- 顶部汇总：在线主机、运行容器、异常 stack、可更新镜像。
- 主机卡片或表格：CPU、内存、磁盘、负载、Docker 状态、更新数。
- 过滤：只看异常、只看有更新。

主机详情：

- 上方实时指标。
- 中间按 stack 折叠。
- stack 展开后显示 service / container。
- 操作按钮用图标 + tooltip。
- 日志抽屉。

## 实现阶段

### Phase 1: host-metrics-exporter

- 实现 `/metrics/json`。
- 支持 CPU、内存、磁盘、load、uptime。
- 支持配置磁盘路径。
- 提供 Dockerfile。
- 提供 compose 部署样例。

### Phase 2: 后端数据源适配

- Dockge Socket.IO 登录和连接池。
- docker-socket-proxy client。
- host-metrics client。
- registry digest client。
- 统一 host snapshot 聚合。

### Phase 3: 基础 UI

- 登录。
- 主机总览。
- 主机详情。
- stack 列表。
- 基础 stack 操作。

### Phase 4: 状态刷新

- 前端轮询或后续 SSE。
- 容器 stats 采集。
- 离线 / 超时状态处理。

### Phase 5: 镜像更新检测

- 镜像引用解析。
- registry digest 查询。
- update 状态缓存。
- 手动刷新和定时刷新。

### Phase 6: 安全和可用性

- 凭据加密。
- 审计日志。
- 操作确认。
- 部署 compose 样例。
- 错误状态和重试策略。

## 测试计划

exporter：

- Linux VPS。
- NAS / iStoreOS。
- 不同磁盘路径。
- exporter 离线。

单主机：

- Dockge 在线、proxy 在线、metrics 在线。
- 正确显示 stacks、containers、metrics。
- start / stop / restart / update 可执行。

多主机：

- 一台在线。
- 一台 Dockge 离线。
- 一台 metrics 离线。
- 首页聚合计数正确。
- 主机折叠展开不串数据。

安全：

- 未登录不能访问 API。
- 前端拿不到远端凭据。
- 写操作记录审计。
- docker-socket-proxy `POST=0` 时无法被 Dashboard 用来写 Docker。

更新检测：

- public image。
- GHCR image。
- pinned tag。
- latest tag。
- 私有 registry 无权限。
- 本地 image missing。
- multi-arch image。

UI：

- 中文文本不溢出。
- 桌面和移动端主机详情可用。
- 日志抽屉长日志不卡死。

## 当前项目状态

导入时当前项目目录：

```text
backend/
  app/
    auth/
    routers/
    services/
    config.py
    database.py
    models.py
    schemas.py

host-metrics-exporter/
  compose.example.yaml
  Dockerfile
  exporter.py
  requirements.txt
```

下一步建议：

1. 先 review 当前 `host-metrics-exporter` 是否满足 Phase 1。
2. review 现有 `backend/app` 脚手架是否完全符合本导入文档的安全约束。
3. 补齐 host 配置加载、凭据加密、SQLite/WAL。
4. 实现 docker-socket-proxy 和 metrics client。
5. 最后接 Dockge Socket.IO。
