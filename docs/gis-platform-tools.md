# GIS Platform 工具集说明

本文档总结 `tools/gis_platform_tool.py` 中注册的 **Hermes 可调 GIS 平台工具**（`toolset`: `gis_platform`）：名称、对应用途与相关后端路径。

**实现位置：** `tools/gis_platform_tool.py`  
**工具集元数据：** `toolsets.py` 中 `gis_platform`

---

## 作用概述

本工具集通过 HTTP 调用外部 **GIS 后端**（管线路网、场站、告警、统计、审计、巡检、拓扑等 REST API），将结果以 **紧凑 JSON** 返回给模型，用于油气/管网类 GIS 监控与运维场景的智能问答与操作。

---

## 配置（环境变量）

| 变量 | 说明 |
|------|------|
| `GIS_API_URL` | 后端基址，默认 `http://localhost:8080` |
| `GIS_API_TOKEN` | 调用受保护接口的 Bearer JWT；与下方「可用性」相关 |
| `GIS_TOOLS_ALLOW_WRITE` | 设为 `true` 时启用**写操作**（增删改、告警确认/解决、规则维护等）；默认关闭 |
| `GIS_ALLOW_ANON` | 设为 `true` 时，在无 Token 时仍视工具为可用（需后端允许匿名） |

**安全说明：** 写操作默认关闭，避免误改生产数据。需要写入时再显式打开 `GIS_TOOLS_ALLOW_WRITE=true`。

**工具可用性：** 默认在配置了 `GIS_API_TOKEN`，或 `GIS_ALLOW_ANON=true` 时，工具对模型可见/可调用（见 `_check_available`）。

---

## 只读与写入

- **只读（Read）：** 查询、列表、概览、拓扑分析等，仅需 Token（或匿名策略允许）即可。
- **写入（Write）：** 名称含 `create` / `update` / `delete` / `ack` / `resolve` 的接口；需 `GIS_TOOLS_ALLOW_WRITE=true`，否则返回明确错误信息。

下表在「类型」列标注 **R**=只读、**W**=写入。

---

## 按功能分类的工具列表

### 1. 认证

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_auth_me` | R | 根据当前 Token 获取当前用户信息 | `GET /api/auth/me` |

### 2. 管线（Pipeline）

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_list_pipelines` | R | 列出管线（GeoJSON FeatureCollection）；可按 `type`（如原油/成品/气等）、`status`（如 normal/warning/repair 等）筛选；返回经压缩的要素摘要 | `GET /api/pipelines` |
| `gis_get_pipeline` | R | 按 ID 获取单条管线（GeoJSON Feature 形态数据） | `GET /api/pipelines/{id}` |
| `gis_list_pipelines_bbox` | R | 在边界框内列出管线（`minLng/minLat/maxLng/maxLat`） | `GET /api/pipelines/bbox` |
| `gis_create_pipeline` | W | 新建管线 | `POST /api/pipelines` |
| `gis_update_pipeline` | W | 按 ID 更新管线 | `PUT /api/pipelines/{id}` |
| `gis_delete_pipeline` | W | 按 ID 删除管线 | `DELETE /api/pipelines/{id}` |

### 3. 场站（Station）

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_list_stations` | R | 列出场站（GeoJSON FeatureCollection）；可按 `type`、`status`（如 online/offline/alarm）筛选 | `GET /api/stations` |
| `gis_get_station` | R | 按 ID 获取单场站 | `GET /api/stations/{id}` |
| `gis_list_stations_by_pipe` | R | 查询绑定到某条管线 ID 的场站 | `GET /api/stations/bindPipe/{pipeId}` |
| `gis_create_station` | W | 新建场站（体为 GeoJSON Feature：Point + properties 等，详见 schema 描述） | `POST /api/stations` |
| `gis_update_station` | W | 按 ID 更新场站 | `PUT /api/stations/{id}` |
| `gis_delete_station` | W | 按 ID 删除场站 | `DELETE /api/stations/{id}` |

### 4. 统计

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_stats_overview` | R | 平台总览类统计 | `GET /api/stats/overview` |

### 5. 告警（Alarm）

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_list_alarms` | R | 列表告警；可选 `resolved`（布尔）、`stationId`；返回最多 100 条摘要 | `GET /api/alarms` |
| `gis_get_alarm` | R | 按整数 ID 取单条告警 | `GET /api/alarms/{id}` |
| `gis_ack_alarm` | W | 确认（Acknowledge）告警 | `POST /api/alarms/{id}/acknowledge` |
| `gis_resolve_alarm` | W | 解决告警，可选 `resolutionNote` | `PUT /api/alarms/{id}/resolve` |

### 6. 告警规则（Alarm rules）

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_list_alarm_rules` | R | 列出告警规则 | `GET /api/alarm-rules` |
| `gis_create_alarm_rule` | W | 新建规则（体为 `rule` 对象） | `POST /api/alarm-rules` |
| `gis_update_alarm_rule` | W | 按整数 ID 更新规则 | `PUT /api/alarm-rules/{id}` |
| `gis_delete_alarm_rule` | W | 按整数 ID 删除规则 | `DELETE /api/alarm-rules/{id}` |

### 7. 审计（Audit）

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_list_audit_logs` | R | 分页/筛选审计日志（username、action、target、startDate、endDate、page、size ≤ 100） | `GET /api/audit-logs` |
| `gis_audit_stats` | R | 审计相关聚合统计 | `GET /api/audit-logs/stats` |

### 8. 巡检计划与记录（Inspection）

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_list_inspection_plans` | R | 列出巡检计划；可选 `status`、`pipelineId` | `GET /api/inspection-plans` |
| `gis_get_inspection_plan` | R | 按 ID 取巡检计划 | `GET /api/inspection-plans/{id}` |
| `gis_create_inspection_plan` | W | 新建计划（体为 `plan`） | `POST /api/inspection-plans` |
| `gis_update_inspection_plan` | W | 按 ID 更新计划 | `PUT /api/inspection-plans/{id}` |
| `gis_delete_inspection_plan` | W | 按 ID 删除计划 | `DELETE /api/inspection-plans/{id}` |
| `gis_list_inspection_records` | R | 列出巡检记录；可选 `planId`、`status` | `GET /api/inspection-records` |
| `gis_get_inspection_record` | R | 按整数 ID 取单条记录 | `GET /api/inspection-records/{id}` |
| `gis_create_inspection_record` | W | 新建记录（体为 `record`） | `POST /api/inspection-records` |
| `gis_update_inspection_record` | W | 按整数 ID 更新记录 | `PUT /api/inspection-records/{id}` |
| `gis_delete_inspection_record` | W | 按整数 ID 删除记录 | `DELETE /api/inspection-records/{id}` |

### 9. 拓扑（Topology）

| 工具名 | 类型 | 用途 | 后端 |
|--------|------|------|------|
| `gis_topology_connections` | R | 查询某管线 ID 的直接连接关系 | `GET /api/topology/connections/{pipeId}` |
| `gis_topology_trace` | R | 从 `startPipeId` 起沿网追溯，`direction`：`both` / `upstream` / `downstream` | `GET /api/topology/trace` |
| `gis_topology_shutoff` | R | 按阀门场站 ID 做关断影响仿真 | `GET /api/topology/shutoff?valveStationId=...` |

---

## 数据与校验说明（摘要）

- **字符串 ID**（管线、场站、计划等）需符合实现中的保守格式：字母数字开头，长度与字符集受 `_ID_RE` 限制（与 CRD-001 等 demo ID 风格一致）。
- **列表类 GeoJSON** 在管线/场站列表中可能被 `_compact_feature_collection` 压缩为 `count` + 若干条 `id/name/status/type` 摘要，以控制上下文体量。
- **告警/规则/巡检记录** 中部分主键为 **整数**（`gis_get_alarm` 等），与字符串管线 ID 区分。

---

## 与部署文档的关系

若需将 Hermes 与 GIS 管道demo/后端联调，可结合仓库内 `docs/gis-pipeline-hermes-deploy-checklist.md` 等检查清单进行环境配置与验证。

---

## 工具数量统计

共 **37** 个工具：只读 **20**，写入 **17**（全部写入均受 `GIS_TOOLS_ALLOW_WRITE` 控制）。
