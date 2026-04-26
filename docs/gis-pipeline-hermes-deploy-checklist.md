# Hermes Agent：与 GIS Pipeline 集成时的配置与部署清单

本文面向 **Hermes-agent 运维与部署**，与 **gis-project** 当前集成方式对齐（BFF 代理聊天、业务用户与会话映射在 GIS 侧）。**不要求修改 Hermes 源码**；以实际部署的 Hermes 版本为准，升级后请核对 HTTP 契约。

GIS 侧接口说明可参考 **gis-project** 仓库根目录的 `hermes-agent-api-integration.md`（与本文互补：请求/响应字段、SSE、`/v1/responses` 等）。

---

## 1. API Server（OpenAI 兼容，默认常监听 8642）

| 序号 | 检查项 | 建议 |
|------|--------|------|
| 1.1 | 监听地址与端口 | 环境变量或配置：`API_SERVER_HOST`、`API_SERVER_PORT`（或 `platforms.api_server.extra.host` / `extra.port`）。须与 GIS `hermes.api-server-base-url` 一致（例如 `http://127.0.0.1:8642`）。 |
| 1.2 | **API Key（强烈建议生产必配）** | `API_SERVER_KEY`（或 `platforms.api_server.extra.key`）。GIS 使用 `hermes.api-server-key`，以 `Authorization: Bearer <token>` 调用。**绑定非本机可访问地址时 Hermes 会拒绝启动**若未配置 Key，或 Key 过弱（占位符）；生产请使用足够随机强度（如 `openssl rand -hex 32`）。未配置 Key 时，**禁止**使用 `X-Hermes-Session-Id` 续聊（Hermes 返回 403），且匿名访问不适合生产。 |
| 1.3 | 对外模型名 | `API_SERVER_MODEL_NAME` / `extra.model_name`：与 `GET /v1/models` 及客户端 `model` 字段期望一致。 |
| 1.4 | 浏览器直连（可选） | 若仍允许浏览器直连 API Server：配置 `API_SERVER_CORS_ORIGINS`。**推荐**仅由 GIS 后端出网调用 Hermes，弱化对 Hermes CORS 的依赖。 |
| 1.5 | 会话头 | 多轮对话使用请求头 `X-Hermes-Session-Id`；GIS BFF 会代发。**勿**依赖浏览器携带该自定义头直连（当前 CORS 预检允许头通常不含此项）。 |
| 1.6 | **回写会话 id** | 每轮响应（含 **SSE**）响应头会带 `X-Hermes-Session-Id`。若首请求未带该头，Hermes 会按内容派生 `session_id`——GIS 须在**首轮完成后**把响应头中的值持久化到 `ai_conversation`（或等价表），后续轮再原样带回，否则会话无法对齐。 |
| 1.7 | **幂等（可选）** | 非流式 `POST /v1/chat/completions` 可带 `Idempotency-Key`；BFF 重试同一业务请求时可降低重复扣费/重复写入风险（指纹含 `model`、`messages`、`tools`、`tool_choice`、`stream`）。 |
| 1.8 | 请求体大小 | 服务端对 POST body 有默认上限（约 1MB 量级）；大图/多模态过多时需压缩或改走对象存储 + URL/文本摘要。 |

**说明**：IM 网关里的 `group_sessions_per_user` / `build_session_key` 与 **api_server** 的 **`X-Hermes-Session-Id` HTTP 会话**是两套机制；GIS 经 BFF 对接时以 **1.5–1.6** 为准。

---

## 2. Dashboard（会话 REST，常与 `hermes web` 同栈，例如 9119）

| 序号 | 检查项 | 建议 |
|------|--------|------|
| 2.1 | 服务可达 | Dashboard 根 URL 与 GIS `hermes.dashboard-base-url` 一致；网络/防火墙允许 **GIS 服务器** 访问。 |
| 2.2 | 鉴权 Token | GIS 可配置 `hermes.dashboard-session-token`（Bearer）；或依赖 GIS 从 Dashboard 首页 HTML 解析 `window.__HERMES_SESSION_TOKEN__`（适合本地，生产建议显式配置 token）。部分部署可复用 `API_SERVER_KEY` 作为 Dashboard 鉴权，视 Hermes 版本而定。 |
| 2.3 | 会话 API | GIS 通过服务端调用 Dashboard 的 `/api/sessions/...`（拉消息、删会话等）。升级 Hermes 后若路径或 JSON 变更，需在 GIS 侧对齐。 |

---

## 3. 模型、工具与工作目录（网关 `config.yaml` / 环境变量）

| 序号 | 检查项 | 建议 |
|------|--------|------|
| 3.1 | 上游 LLM | 供应商、API Key、模型名等在 Hermes 网关配置；**不要**把模型 Key 暴露给浏览器或 GIS 前端。 |
| 3.2 | API Server 工具集 | `platform_toolsets.api_server`（或当前版本等价项）：决定 api_server 上可用工具。 |
| 3.3 | 工作目录 | `TERMINAL_CWD`、`MESSAGING_CWD` 等：影响 `read_file` 与上下文文件发现；多用户/多租户场景下注意目录隔离（运维级）。 |
| 3.4 | 记忆 / Memory | `memory.*`、磁盘 `memories/` 等：多用户共享同一 Hermes 进程时，注意是否会产生**跨用户记忆串扰**；严格隔离可考虑分实例或分数据目录。 |

---

## 4. 网络、代理与健康检查

| 序号 | 检查项 | 建议 |
|------|--------|------|
| 4.1 | 拓扑 | Hermes API Server 与 Dashboard 建议仅内网或对 GIS 后端白名单暴露，不必对公网开放。 |
| 4.2 | 反向代理 | 若经 Nginx/Ingress：对 `POST /v1/chat/completions`（尤其 `stream: true`）配置足够长的**超时**，并对 SSE 关闭不当**缓冲**（例如 `proxy_buffering off`、`proxy_read_timeout` 加大；Hermes 响应头含 `X-Accel-Buffering: no`）。 |
| 4.3 | 健康检查 | `GET /health`、`GET /health/detailed` 或 `GET /v1/health`：供运维探活。 |

---

## 5. 与 GIS `application.yml` 的对应关系（自检用）

| GIS 配置项 | Hermes 侧对应 |
|------------|----------------|
| `hermes.api-server-base-url` | API Server 根 URL（与 1.1 一致）。 |
| `hermes.api-server-key` | 与 `API_SERVER_KEY` 一致（与 1.2 一致）。 |
| `hermes.dashboard-base-url` | Dashboard 根 URL（与 2.1 一致）。 |
| `hermes.dashboard-session-token`（可选） | Dashboard Bearer；见 2.2。 |

---

## 6. 可选加固（按安全与合规）

- 按工厂/租户部署多套 Hermes 或多套工作目录配置，与 GIS 后续租户路由配合。
- 对 Hermes 入口做 IP 白名单或 mTLS，仅允许 GIS 后端访问。
- 版本升级后对照本仓库 `gateway/platforms/api_server.py` 等源码核对 HTTP 行为。

---

## 7. 小结

- Hermes **无需为 GIS 会话映射单独改代码**；重点是 **API Server Key、地址**、**Dashboard 地址与 Token**、以及 **模型 / 工具 / 工作目录 / 记忆** 的配置与可达性。
- GIS 负责：JWT 用户、`ai_conversation` 与 **`X-Hermes-Session-Id` 绑定（含首轮从响应头回写）**、限流与审计；客户端中途断开流式请求时 Hermes 会 **interrupt** Agent，BFF 侧若有取消逻辑需与产品预期一致。
- 若后续需 OpenAI **Responses** 链式 API（`previous_response_id`）或 **`/v1/runs` 事件流**，以 `gateway/platforms/api_server.py` 为准扩展 GIS 客户端；当前清单以 **`/v1/chat/completions`** 为主路径。
