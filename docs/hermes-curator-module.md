# Hermes Curator 模块完整学习文档

本文档基于源码 `agent/curator.py` 及 CLI 封装 `hermes_cli/curator.py` 整理。所有路径均以当前 **profile** 的 `HERMES_HOME` 为准（默认 profile 下等价于 `~/.hermes/`；多 profile 时见 [`hermes_constants.display_hermes_home()`](hermes_constants.py)）。

---

## 一、模块概述

### 1. 定位

**Curator** 是技能后台管护编排器，属于 Hermes 框架内置的**后台辅助任务**：专门负责对 **Agent 自建技能**进行全生命周期的自动化维护与规整（合并碎片、状态流转、归档），与主会话推理解耦。

### 2. 核心设计理念

| 理念 | 说明 |
|------|------|
| 非定时 Cron 独占守护 | **空闲/周期触发**：由 `maybe_run_curator()` 在合适时机发起；Gateway 侧仅在既有 cron ticker 上「捎带」轮询，真正是否干活由 `interval_hours` 等条件决定。 |
| 纯算法 + LLM 分层 | 先做 **无 LLM** 的自动状态流转，再 **fork 独立 `AIAgent`** 执行伞式聚类与规整 prompt。 |
| 只归档、不物理删除 | 归档目录可恢复；LLM prompt 明确禁止 delete。 |
| 范围收口 | 仅处理 **agent-created** 技能（`tools/skill_usage.is_agent_created`）；bundled / hub 安装技能不在候选列表。 |
| **置顶（pinned）** | `pinned=yes` 的技能在自动流转中 **整段跳过**；LLM 侧 prompt 也要求不得触碰。 |
| 后台执行 | 默认在 **daemon 线程** 中跑 LLM  pass，不阻塞调用方；fork 的 Agent 还把 stdout/stderr 导向 `/dev/null`，避免污染前台终端。 |
| 可审计 | 每次运行（尽力）写入 **机器可读 `run.json` + 人读 `REPORT.md`**，状态文件记录摘要与报告路径。 |

### 3. 核心职责

1. 按「最后活跃」锚点时间自动切换技能生命周期：**活跃（active）/ 陈旧（stale）/ 归档（archived）**。  
2. 后台拉起 **独立** LLM Agent，按 `CURATOR_REVIEW_PROMPT` 做伞式聚类、合并、补丁与归档建议执行。  
3. 推动碎片技能收拢为 **大类伞技能 + `references/`、`templates/`、`scripts/`** 子文件结构（由 prompt 约束 + `skill_manage` / `terminal` 等工具落实）。  
4. 持久化 **`.curator_state`**（运行时间、暂停、统计、摘要、最近报告路径等）。  
5. 提供统一入口 **`maybe_run_curator()`**，供 CLI / Gateway 等在合适时机触发。

---

## 二、默认配置参数

源码默认值（`agent/curator.py`）与 `hermes_cli/config.py` 中 `DEFAULT_CONFIG["curator"]` 一致：

```python
DEFAULT_INTERVAL_HOURS = 24 * 7   # 管护最小间隔：7 天（按小时存配置）
DEFAULT_MIN_IDLE_HOURS = 2         # 主 Agent 空闲门槛（见下文「空闲门控」）
DEFAULT_STALE_AFTER_DAYS = 30      # 锚点早于此时 → active 可标为 stale
DEFAULT_ARCHIVE_AFTER_DAYS = 90    # 锚点早于此时 → 自动 archive
```

**优先级**：`config.yaml` 的 `curator.*` **覆盖**代码默认值（通过 `_load_config()` → `load_config()` 读取）。

### `config.yaml` 中 `curator` 段（摘录）

| 键 | 含义 |
|----|------|
| `enabled` | 是否启用（默认 `true`） |
| `interval_hours` | 两次运行之间的最小间隔（小时） |
| `min_idle_hours` | 调用方传入空闲秒数时，低于此则 **不运行** |
| `stale_after_days` | 进入 stale 的天数阈值 |
| `archive_after_days` | 自动归档天数阈值 |
| `auxiliary` | 默认配置里预留 `provider` / `model`；**当前** `agent/curator.py` 的 `_run_llm_review()` 使用主配置 `model` 段 + `resolve_runtime_provider()` 解析凭证与模型，如需与「文档注释中的 auxiliary」完全一致，请以源码为准。 |

---

## 三、目录与文件结构

### 1. 状态文件路径

```text
<HERMES_HOME>/skills/.curator_state
```

JSON：安全读写得 `_default_state()` 与 `load_state()` / `save_state()`（未知键会过滤，仅保留白名单字段及 `_` 前缀扩展键）。

常见字段包括：`last_run_at`、`last_run_duration_seconds`、`last_run_summary`、`paused`、`run_count`，以及成功写报告后的 `last_report_path` 等。

### 2. 日志报告路径

```text
<HERMES_HOME>/logs/curator/YYYYMMDD-HHMMSS[-suffix]/
  ├─ run.json    # 机器可读完整运行数据（前后快照 diff、工具调用等）
  └─ REPORT.md   # 人类可读运维报告
```

同一秒内重复运行会依次使用 `-2`、`-3`… 后缀目录（见 `_write_run_report()`）。

### 3. 归档目录

```text
<HERMES_HOME>/skills/.archive/
```

归档技能存放于此；**不删除**，可通过 CLI 或手动 `mv` 恢复。

---

## 四、核心模块函数总览

| 函数 | 作用 |
|------|------|
| `_state_file()` | 返回 Curator 状态文件路径 |
| `load_state()` | 安全加载状态；不存在或损坏则回退默认 |
| `save_state()` | `mkstemp` 写临时文件 → `fsync` → `os.replace` 原子替换 |
| `_load_config()` | 从 `config.yaml` 读取 `curator` 段 |
| `is_enabled()` / `get_*()` | 配置访问封装 |
| `_parse_iso()` | 解析 ISO 时间字符串；失败返回 `None` |
| `should_run_now()` | **静态**门控：`enabled`、非 `paused`、距 `last_run_at` 已满 `interval_hours`（**不含**空闲时长） |
| `apply_automatic_transitions()` | 纯算法遍历 agent-created 技能，更新 stale / archived / reactivated |
| `_render_candidate_list()` | 生成带 state/pinned/计数/last_used 的清单字符串 |
| `_run_llm_review()` | 构造 fork `AIAgent`，`run_conversation` 执行 prompt，收集 `tool_calls` 与 final |
| `run_curator_review()` | **主流程**：自动流转 → **先写** `last_run_at`（防崩溃重复触发）→ 后台或同步 LLM → 报告 → 更新状态 |
| `_reports_root()` | `<HERMES_HOME>/logs/curator` |
| `_write_run_report()` | 写入 `run.json` + `REPORT.md` |
| `_render_report_markdown()` | 结构化 payload → Markdown |
| `maybe_run_curator()` | **对外主入口**：`should_run_now()` + 可选 `idle_for_seconds` → `run_curator_review()` |

---

## 五、运行触发机制

### 非 Cron 独占

- **不是**单独长期驻留的 cron 进程；由集成点在适当时机调用 `maybe_run_curator()`。  
- **Gateway**：在已有 cron ticker 中间隔调用一次 `maybe_run_curator()`；真正是否执行仍由 `should_run_now()` 的 7 天（默认）等条件决定。  
- **CLI**：会话启动时尝试 `maybe_run_curator(...)`（见 `cli.py` 中注释）。

### 触发条件（逻辑拆解）

1. **`should_run_now()` 为真**：`curator.enabled`（默认开）、未暂停、`last_run_at` 为空 **或** 已超过 `interval_hours`。  
2. **空闲门控（可选）**：若调用方传入 **`idle_for_seconds`**，则必须 `>= min_idle_hours * 3600`，否则直接返回 `None`。  
   - 若 **`idle_for_seconds` 为 `None`**，代码 **不会**检查空闲时长。  
   - 当前 **CLI 启动**与 **Gateway ticker** 传入的是 `float("inf")`，即 **总是满足**空闲条件（与「配置里 2 小时」可同时存在：配置保留给未来/其他调用方传入真实空闲时间时使用）。

满足后默认 **`run_curator_review()` → daemon 线程** 跑 LLM 段，主路径立即返回。

---

## 六、技能状态自动流转规则（纯算法）

状态枚举以 `tools/skill_usage` 为准（`STATE_ACTIVE`、`STATE_STALE`、`STATE_ARCHIVED`）。

### 锚点时间

对每个 **非 pinned** 的 agent-created 技能：

1. `last_used_at`（有效 ISO）  
2. 否则 `created_at`  
3. 否则 **当前 `now`**（避免新建技能立刻被误归档）

无时区的时间会按 UTC 补齐。

### 流转逻辑（与源码一致）

设 `stale_cutoff = now - stale_after_days`，`archive_cutoff = now - archive_after_days`，`anchor` 为上述锚点，`current` 为当前 state。

1. **`anchor <= archive_cutoff` 且 `current != archived`**：调用 `archive_skill(name)`（成功则计数 `archived`）。  
2. **否则若 `anchor <= stale_cutoff` 且 `current == active`**：`set_state(stale)`（`marked_stale`）。  
3. **否则若 `anchor > stale_cutoff` 且 `current == stale`**：视为重新被活跃使用 → **`set_state(active)`**（`reactivated`）。

**Pinned**：循环开始即 `continue`，不参与任何自动流转。

---

## 七、LLM 智能规整（`CURATOR_REVIEW_PROMPT`）

### 核心目标

拒绝「一会话一微技能」；构建 **类级伞技能库**：宽 `SKILL.md` + `references/` / `templates/` / `scripts/` 承载会话细节。

### 五条硬性规则（摘自 prompt 意图）

1. 不碰 bundled / hub 安装技能；候选列表已预过滤为 agent-created。  
2. 绝不删除；**最高**动作为归档到 `.archive/`。  
3. 不碰 `pinned=yes`。  
4. 合并判断以 **内容重叠** 为准，不拿 `use_count` 当拒绝理由。  
5. 不因「触发略有不同」拒绝合并；标准是 **人类维护者是否会写成一个大类 + 多小节**。

### 三种收拢方式（prompt 指导）

- **并入已有伞技能**：扩写 `SKILL.md` 小节，兄弟技能归档。  
- **新建伞技能**：`skill_manage action=create`，再归档被吸收的窄技能。  
- **降级为附属文件**：会话级细节进 `references/`、`templates/`、`scripts/`，必要时 `terminal` + `mv`。  

工作流强调：**前缀/领域簇** → 识别 umbrella 类名 → 多轮迭代直到聚类机会收敛；窄命名（PR 号、单行报错、session  artifacts 等）倾向并入伞下小节或 support 文件。

### Fork Agent 行为要点

- `AIAgent(..., max_iterations=9999, quiet_mode=True, platform="curator", skip_context_files=True, skip_memory=True)`。  
- 关闭 memory/skill nudge 间隔，避免管护再拉起管护。  
- 同步模式下同样重定向 stdout/stderr，避免刷屏。

---

## 八、一次完整 Curator 运行全流程

1. **`run_curator_review()` 开始**（ UTC `start`）。  
2. **`apply_automatic_transitions(start)`** — 纯算法计数 `checked/marked_stale/archived/reactivated`。  
3. **立即** `load_state()` → 写入 `last_run_at`、`run_count`、`last_run_summary`（仅 auto 部分）→ `save_state()`，防止 LLM 过程中崩溃导致短时间重复全量触发。  
4. **默认**：`_llm_pass` 在 **daemon 线程**执行：  
   - 抓取 **LLM 前** `agent_created_report()` 快照与 `before_names`。  
   - 若已无候选，跳过 LLM，仅写摘要。  
   - 否则拼接 `CURATOR_REVIEW_PROMPT + 候选列表`，`_run_llm_review`。  
   - 计算耗时，更新 `last_run_duration_seconds`、完整 `last_run_summary`。  
   - **`_write_run_report`**：diff 归档/新增/状态迁移，写 `run.json` 与 `REPORT.md`；成功则 `last_report_path`。  
   - `save_state(state2)`，可选 `on_summary` 回调。  
5. 主线程立即返回 `started_at`、`auto_transitions`、`summary_so_far`（此时 LLM 可能仍在后台）。

---

## 九、工程设计亮点

| 点 | 实现要点 |
|----|----------|
| 高容错 | 大量路径 `try/except` + `logger.debug`，报告写入失败不拖垮管护主逻辑 |
| 状态文件安全 | 临时文件 + `fsync` + `os.replace` |
| 时间一致 | 比较与 `last_run_at` 写入使用 **UTC**；naive 时间按 UTC 解释 |
| 分层清晰 | 配置 / 状态 / 自动流转 / LLM / 报告 / 入口分离 |
| 与主会话隔离 | 独立 `AIAgent`、高迭代上限、屏蔽终端输出、不写主 session 记忆 |
| 可审计可恢复 | `run.json` 全量；`REPORT.md` 含恢复指引；归档可 CLI 恢复 |

---

## 十、常用运维操作

| 操作 | 方式 |
|------|------|
| 查看状态与技能统计 | `hermes curator status` |
| 立即跑一轮（默认后台 LLM） | `hermes curator run`；同步等待 LLM：`hermes curator run --sync` |
| 暂停 / 恢复 | `hermes curator pause` / `hermes curator resume` |
| 置顶/取消置顶（跳过自动流转） | `hermes curator pin <skill>` / `hermes curator unpin <skill>` |
| 恢复归档技能 | `hermes curator restore <skill-name>` |
| 读原始状态文件 | `<HERMES_HOME>/skills/.curator_state` |
| 浏览归档 | `<HERMES_HOME>/skills/.archive/` |
| 阅读运行报告 | `<HERMES_HOME>/logs/curator/<时间戳>/REPORT.md`，明细见同目录 `run.json` |

---

## 附录：源码入口参考

- 管护实现：`agent/curator.py`  
- CLI：`hermes_cli/curator.py`  
- 默认配置：`hermes_cli/config.py` → `DEFAULT_CONFIG["curator"]`  
- CLI 启动调用：`cli.py`（`maybe_run_curator`）  
- Gateway 捎带轮询：`gateway/run.py`（cron ticker 内 `maybe_run_curator`）
