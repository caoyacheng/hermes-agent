# 企业聊天系统（从 0 开发）+ Hermes Bot 统一聊天方案

**版本**：1.0  
**目标**：在企业内构建一个支持 **人↔人**、**人↔Hermes** 的统一聊天系统；同时与 Hermes-agent 的 **多租户（tenant）隔离部署**方案兼容。  
**关联文档**：  
- `enterprise-multi-tenant-web-architecture.md`（Hermes 多租户总体架构）  
- `enterprise-multi-tenant-deploy-and-config.md`（Hermes 配置与部署）  

---

## 1. 总体建议（先说结论）

- **把 Hermes 当成“机器人用户（bot member）”接入你们的聊天系统**，而不是让 Hermes 承载整套 IM。
- **聊天链路与机器人链路解耦**：用户发消息必须快速落库并推送；Hermes 的调用走异步 Worker，失败可重试，不阻塞群聊体验。
- **强制分区键**：所有业务表、缓存 key、对象存储 key、事件都必须包含 `tenant_id` 与 `room_id`，避免串数据。
- Hermes 接入推荐用 **`POST /v1/responses`**：你们只需保存 `room_id → previous_response_id`（按租户隔离），多轮上下文由 Hermes 服务端维护。

---

## 2. 逻辑架构

```mermaid
flowchart TB
  subgraph FE["前端"]
    Web[Web / 桌面端 / 移动端]
  end

  subgraph Edge["边缘层"]
    SSO[SSO / WAF]
    BFF[Chat BFF (HTTP+WS)]
  end

  subgraph Core["聊天核心（Chat Core）"]
    API[Chat Core API]
    DB[(Postgres)]
    MQ[(消息队列 / 事件总线)]
    Obj[(对象存储)]
  end

  subgraph Bot["Bot 编排层"]
    Worker[Hermes Bot Worker]
    Reg[(租户注册表)]
  end

  subgraph Hermes["Hermes 多租户实例池"]
    H1[Hermes Tenant A]
    H2[Hermes Tenant B]
    HN[Hermes Tenant N]
  end

  Web --> SSO --> BFF --> API
  API --> DB
  API --> MQ
  BFF <--> API
  BFF --> Obj
  Worker --> MQ
  Worker --> API
  Worker --> Reg
  Worker --> H1
  Worker --> H2
  Worker --> HN
```

**说明**：

- **Chat Core**：你们自研的“人↔人聊天”核心能力（房间、成员、消息、附件、历史）。
- **BFF**：统一鉴权、限流、WebSocket、上传预签名等；也可以把 WS 直接放 Core，BFF 做纯网关。
- **MQ**：承载 `message.created` 等事件；Worker 消费事件触发 Hermes。
- **Hermes Bot Worker**：决定何时调用 Hermes、如何裁剪上下文、如何回写 bot 消息、如何重试与告警。

---

## 3. 触发规则（Hermes 参与群聊的方式）

建议从 2 个规则起步（简单、可控、易灰度）：

1. **@Hermes**：消息包含 `@hermes`（或提及 bot 成员）。
2. **/ask 命令**：`/ask ...`（便于机器解析与权限控制）。

可选扩展：

- “房间默认订阅 bot”（某些房间的 bot 自动参与，但仍建议只对明确触发/命令回应）。
- 关键词触发（慎用，易噪声与成本失控）。

---

## 4. 上下文策略（成本与准确率的核心）

群聊必须控制上下文，推荐默认策略：

- **输入给 Hermes 的消息集合**：
  - 触发消息（包含 @hermes / /ask 的那条）
  - 最近 N 条上下文（例如 20 条，按 token 上限截断）
  - 被引用/回复链（若有 `quoted_message_id`，向上追 3~5 层）
  - 房间的系统设定（主题、规范、知识库范围、禁止事项）
- **不建议**：把整个房间历史无差别喂给 Hermes（成本、噪声与泄漏风险都很高）。

---

## 5. Hermes 接入方式（推荐 `/v1/responses`）

### 5.1 为什么推荐 `/v1/responses`

- Worker 只需要保存 `previous_response_id`，不用每次拼全量 `messages`。
- 多轮对话状态由 Hermes 服务端维护，客户端/你们系统更轻。

### 5.2 Bot 状态表（必须）

维护映射：`(tenant_id, room_id, bot_id) -> previous_response_id`。

- 新房间首次触发：`previous_response_id = null`，后续更新。
- 若你们希望“一个房间多个 bot/多个 persona”，用 `bot_id` 区分即可。

### 5.3 幂等与重试

- Worker 消费 `message.created` 时必须 **幂等**：同一触发消息只能产生 0 或 1 条 bot 回复（或按策略多条），用 `bot_jobs` / `dedupe_key` 控制。
- Hermes 调用失败：指数退避重试 + 最大次数 + DLQ（死信队列）+ 告警。

---

## 6. 最小数据模型（推荐 Postgres）

> 目标是 Phase 1~2 可上线；更多功能（已读、多端同步、全文搜索、权限细化）可迭代。

### 6.1 核心表（最小可用）

- `tenants(id, name, status, created_at)`
- `users(id, tenant_id, sso_subject, display_name, created_at)`
- `rooms(id, tenant_id, type['dm'|'group'], title, created_by, created_at)`
- `room_members(room_id, user_id, role, joined_at)`
- `messages(id, tenant_id, room_id, sender_type['user'|'bot'], sender_id, content_json, created_at, edited_at, deleted_at)`
- `attachments(id, tenant_id, uploader_id, type, storage_key, size, sha256, created_at)`
- `message_attachments(message_id, attachment_id)`
- `bot_state(tenant_id, room_id, bot_id, previous_response_id, updated_at)`  ← 关键

建议索引（示例）：

- `messages(tenant_id, room_id, created_at desc)`
- `room_members(room_id, user_id)`
- `attachments(tenant_id, created_at)`

### 6.2 `content_json` 建议形态

- `text: string`
- `mentions: [{type: 'user'|'bot', id: string}]`
- `quoted_message_id?: string`
- `images?: [{attachment_id?: string, url?: string}]`
- `metadata?: {...}`（保留扩展位）

---

## 7. API 设计（面向前端，走 BFF）

> 以下为建议接口；你们可按栈（REST/GraphQL）调整。关键是：**鉴权在 BFF、所有请求都隐含 tenant**。

### 7.1 鉴权与会话

- `POST /auth/login`：SSO 回调后建立服务端 session 或下发 JWT
- 后续请求从 session/JWT 推导 `tenant_id` 与 `user_id`（禁止前端自填）

### 7.2 房间与消息

- `POST /rooms`：创建房间
- `GET /rooms`：我的房间列表
- `GET /rooms/{room_id}/messages?before=...&limit=...`：拉历史
- `POST /rooms/{room_id}/messages`：发消息（**必须快速返回**）

### 7.3 实时推送（推荐 WebSocket）

- `WS /ws`：订阅房间消息事件（加入/离开房间可发控制帧）

### 7.4 附件上传（推荐对象存储直传）

- `POST /attachments/presign` → 返回预签名 URL 与 `attachment_id`
- 前端 `PUT` 到对象存储
- 发消息时引用 `attachment_id`（或 URL）

---

## 8. 事件总线（MQ）与 Worker 编排

### 8.1 事件（示例）

`message.created`：

- `tenant_id`
- `room_id`
- `message_id`
- `sender_type`
- `created_at`
- 可选：`mentions`、`has_attachments`

### 8.2 Worker 处理流程（建议）

1. 消费 `message.created`。
2. 读取消息内容与房间成员，判断是否触发（@hermes 或 /ask）。
3. 读取 `bot_state`（`previous_response_id`），并拉取上下文消息（最近 N 条 + 引用链 + 房间系统设定）。
4. 调用 Hermes（按 `tenant_id` 路由到该租户 Hermes 实例）：
   - `POST /v1/responses`，携带 `previous_response_id`（若有）
5. 解析 Hermes 输出文本（及结构化结果，若你们做了），写入一条 `messages`，`sender_type='bot'`。
6. 更新 `bot_state.previous_response_id`。
7. 若失败：按策略重试；超过阈值进入 DLQ，并写入可观测事件与告警。

---

## 9. Hermes 多租户路由与部署对接

### 9.1 路由原则

- Worker 绝不直接相信来自前端的 `tenant_id`；`tenant_id` 由 Chat Core/BFF 的鉴权结果确定。
- Worker 根据 `tenant_id` 查询 **租户注册表**，获取该租户 Hermes 的 `base_url` 与凭证引用。
- 调 Hermes 时使用 **该租户的 `API_SERVER_KEY`**（`Authorization: Bearer ...`）。

### 9.2 与 Hermes 部署方案的对应

本设计与“每租户一套 Hermes（独立 `HERMES_HOME`）”完全对齐：每个 `tenant_id` 只有一个（或一组）Hermes 后端，不存在跨租户读写同一会话库的问题。\n
具体部署与配置步骤见：`enterprise-multi-tenant-deploy-and-config.md`。

---

## 10. 安全、合规与审计（最小集）

- **唯一入口**：浏览器只访问 BFF；BFF/Worker 才能访问 Hermes 内网地址与 `API_SERVER_KEY`。
- **最小审计字段**：`tenant_id`、`user_id`、`room_id`、`message_id`、`action`、`timestamp`、`source_ip`。
- **内容合规（可选）**：在 Worker 侧对输入/输出做敏感词/数据分类检测；超标则拒答或降级。
- **速率与配额**：对 `tenant_id`、`room_id`、`user_id` 设置并发/调用频率上限（推荐在 Worker + BFF 双层做）。

---

## 11. 分阶段交付（建议）

### Phase 1：人↔人聊天 MVP（先稳定核心）

- 租户/用户/房间/成员/消息落库
- WebSocket 推送（或 SSE）
- 附件直传（对象存储）+ 消息引用附件
- 最小审计日志

### Phase 2：Hermes Bot 接入

- `message.created` 事件 + Worker
- @hermes 与 /ask 触发
- `/v1/responses` 集成 + `bot_state` 持久化
- 重试/DLQ/告警

### Phase 3：体验与运营能力

- 已读/未读、消息编辑撤回
- 房间级系统设定（Bot 行为与知识库范围）
- 搜索、置顶、引用链增强
- 统计与计费（按 `tenant_id` 与 bot 调用量）

---

## 12. 参考

- Hermes 多租户总体：`enterprise-multi-tenant-web-architecture.md`
- Hermes 配置与部署：`enterprise-multi-tenant-deploy-and-config.md`
- Hermes API Server：`website/docs/user-guide/features/api-server.md`

---

## 13. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-04-26 | 初稿：从 0 构建聊天系统 + Hermes Bot 统一聊天 |

