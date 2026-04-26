# 企业多租户场景：Hermes-agent 配置与部署指南

**版本**：1.0  
**关联文档**：[`enterprise-multi-tenant-web-architecture.md`](./enterprise-multi-tenant-web-architecture.md)（总体架构；本文聚焦 **配置 + 部署**，**不改 Hermes 代码** 前提下的落地步骤）

---

## 1. 总体顺序

1. **为每个租户准备一块盘**：一个目录或一条 Kubernetes PVC → 即该租户的 **`HERMES_HOME`**。
2. **首次初始化**：将 Hermes 所需目录与文件放入该路径（init 容器、一次性 Job，或供应流水线从模板拷贝）。
3. **写 Secret**：该租户的 `API_SERVER_KEY`、以及 `.env` 中的模型/供应商密钥（若走统一推理网关可简化密钥面）。
4. **写 ConfigMap（可选）**：各租户共用的 `config.yaml` 模板；差异用 Secret 或小片段 overlay。
5. **启动工作负载**：使用官方或自建 `hermes-agent` 镜像，进程入口为 **`hermes gateway`**（与本地一致），环境变量指向 **`HERMES_HOME`**。
6. **Service 与健康检查**：集群内暴露 API 端口；就绪探针请求 **`GET /health`** 或 **`GET /health/detailed`**。
7. **BFF / 注册表**：记录 `tenant_id → Hermes 内网 Base URL`；转发时在 `Authorization` 中携带该租户的 **`Bearer <API_SERVER_KEY>`**。

---

## 2. 配置项

### 2.1 环境变量（每租户 Pod / 进程）

| 用途 | 典型设置 |
|------|----------|
| 数据根 | **`HERMES_HOME=/data/hermes`**（PVC 挂载到该路径） |
| 启用 API | **`API_SERVER_ENABLED=true`** |
| API 鉴权 | **`API_SERVER_KEY=...`**（**每租户不同**） |
| 监听地址 | **`API_SERVER_HOST=0.0.0.0`** |
| 端口 | **`API_SERVER_PORT=8642`**（或与 Ingress 一致） |
| CORS | 仅当浏览器 **直连** Hermes 时需要 **`API_SERVER_CORS_ORIGINS`**；推荐浏览器 **只访问 BFF**，由 BFF 调集群内 Service，可不对公网开放 Hermes |

模型、工具集、平台开关等仍在各租户 **`HERMES_HOME/config.yaml`** 与 **`HERMES_HOME/.env`** 中维护，与单机使用方式相同。

### 2.2 `HERMES_HOME` 目录内容

与官方 **profile** 一致，通常包含：`config.yaml`、`.env`、`sessions/`、`memories/`、`skills/`、日志与 gateway 状态等。详见 `hermes_cli/profiles.py` 与 `AGENTS.md`（Profiles）。

**首次落盘方式示例**：

- **initContainer**：从 ConfigMap 或镜像内模板将文件拷贝到空 PVC；或  
- **一次性 Job** 执行初始化；或  
- 供应流水线生成 tarball / 目录后挂载。

### 2.3 共享只读层（可选）

- 在 Pod 上 **额外挂载只读卷**（如 `/mnt/org-readonly`），存放企业标准 skills、制度文档等。  
- 通过 **符号链接** 或 **config 中的路径** 指向只读挂载；**勿**将多租户可写状态（SQLite、sessions）放在共享可写卷。

### 2.4 仅 Web / API 时的网关面

若不需要 Telegram、Slack 等，在 **`config.yaml`** 中关闭对应平台，仅保留 **API Server**，以减小攻击面与凭证管理成本。

---

## 3. Kubernetes 部署

### 3.1 每租户最小资源集合

| 资源 | 说明 |
|------|------|
| `PersistentVolumeClaim` | 绑定到 Pod 的 `HERMES_HOME` |
| `Secret` | `API_SERVER_KEY`、LLM 等敏感项 |
| `ConfigMap` | 公共 `config.yaml`（可选） |
| `Deployment` 或 `StatefulSet` | 运行 `hermes gateway`；**每租户单副本** 与 SQLite 会话存储最简单；多副本需单独评估 |
| `Service` | `ClusterIP`，端口与 `API_SERVER_PORT` 一致 |

### 3.2 Pod 逻辑示例

以下字段需按实际镜像、命名空间与存储类调整：

```yaml
spec:
  containers:
    - name: hermes
      image: your-registry/hermes-agent:tag
      env:
        - name: HERMES_HOME
          value: /data/hermes
        - name: API_SERVER_ENABLED
          value: "true"
        - name: API_SERVER_HOST
          value: "0.0.0.0"
        - name: API_SERVER_PORT
          value: "8642"
        - name: API_SERVER_KEY
          valueFrom:
            secretKeyRef:
              name: hermes-tenant-acme
              key: api_server_key
      volumeMounts:
        - name: data
          mountPath: /data/hermes
        - name: readonly-skills
          mountPath: /mnt/org-readonly
          readOnly: true
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: hermes-acme-pvc
    - name: readonly-skills
      persistentVolumeClaim:
        claimName: org-readonly-pvc
```

**进程入口**：与本地一致，例如 **`hermes gateway`**（以镜像 `ENTRYPOINT` / `args` 为准）。

### 3.3 健康检查

| 探针 | 建议 |
|------|------|
| `readinessProbe` | `httpGet` → `path: /health` 或 `/health/detailed`，端口与 API Server 一致 |
| `livenessProbe` | 可用同一 `path`；`periodSeconds` 适当放宽，避免长任务期间误杀 |

### 3.4 动态租户数量

- **Helm**：`helm install hermes-<tenantId> -f values-<tenantId>.yaml`；或  
- **Argo CD ApplicationSet**：由租户列表生成多个 Application；或  
- **Operator**：监听租户 CRD，创建上述资源并回写注册表中的 `hermes_base_url`。

---

## 4. 非 Kubernetes（虚拟机 / Docker Compose）

- **每个租户**：独立目录作为 **`HERMES_HOME`**（卷映射到宿主机），一套环境变量，一条 **`hermes gateway`** 进程或一个 compose service。  
- **多个租户**：多个 compose 工程或多个 service，各自 **`HERMES_HOME`** 与 **`API_SERVER_KEY`** 不同。

---

## 5. 与 BFF 的约定

- **注册表**保存：`tenant_id` → 内网 `https://hermes-tenant-xxx.namespace.svc.cluster.local:8642`（示例）及凭证引用。  
- **浏览器**只调用 BFF；BFF 将 `POST /v1/chat/completions` 或 `POST /v1/responses` **转发**至对应租户 Service，并设置 **`Authorization: Bearer <API_SERVER_KEY>`**。  
- **流式**：SSE 由 BFF 透传至前端。

---

## 6. 参考

| 主题 | 位置 |
|------|------|
| API Server 开关与端点 | `website/docs/user-guide/features/api-server.md` |
| 总体架构与「Hermes 是否改代码」 | [`enterprise-multi-tenant-web-architecture.md`](./enterprise-multi-tenant-web-architecture.md) §13 |
| Profile / `HERMES_HOME` | `hermes_cli/profiles.py`、`AGENTS.md` |

---

## 7. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-04-24 | 初稿：配置与部署步骤 |
