# 多套 Hermes 实例：共享与隔离说明

本文说明在同一台机器上使用 **默认实例**（`HERMES_HOME` ≈ `~/.hermes`）与 **命名 profile**（例如 `~/.hermes/profiles/instance2/`）时，**哪些资源是共享的、哪些是各自隔离的**。便于排错（端口冲突、双 bot、密钥范围）与部署规划。

**相关命令：** `hermes -p <profile> …`、`hermes profile list|create|use|delete`  
**权威路径规则：** `get_hermes_home()` / `display_hermes_home()`（见 `hermes_constants.py`）、`hermes_cli/profiles.py`。

---

## 一、按 `HERMES_HOME` 完全隔离的部分

每个 profile 拥有**自己的根目录**（通过启动时设置环境变量 `HERMES_HOME`，或由 `hermes -p <name>` 在进程最早期解析并设置）。以下路径均相对于**当前** `get_hermes_home()`，因此**在实例之间互不覆盖**（除非你用软链接或 `--clone-all` 刻意共享磁盘上的同一文件）。

| 类别 | 典型路径（命名 profile 下） | 说明 |
|------|-----------------------------|------|
| 主配置 | `config.yaml` | 模型、工具集、gateway 行为、display 等 |
| 密钥与 dotenv | `.env` | API Key、网关相关环境变量等（与 `config.yaml` 配合） |
| 认证存储 | `auth.json` 等 | OAuth / 门户凭据、`hermes auth` 写入的数据 |
| 会话与历史 | `sessions/`、会话数据库（若存在） | 聊天历史、resume 列表 |
| 记忆与身份 | `memories/`、`SOUL.md` 等 | 长期记忆、人设文件 |
| 日志 | `logs/` | `agent.log`、`errors.log`、`gateway.log` 等 |
| 用户技能目录 | `skills/` | `get_skills_dir()` → `HERMES_HOME/skills` |
| 用户插件目录 | `plugins/` | 通用插件扫描路径之一：`get_hermes_home() / "plugins"` |
| Gateway 运行态 | `gateway.pid`、`gateway_state.json` 等 | 与 launchd / 本机第二套网关进程对应 |
| Cron | `cron/` | 定时任务数据与配置落盘 |
| 子进程隔离 HOME | `home/` | 存在时作为工具子进程的 `HOME`（git/ssh/npm 等配置不串 profile） |
| 其它状态 | `workspace/`、`skins/`、`plans/`、`optional-skills/`（默认布局下）等 | 随各 profile 独立 |

**结论：** 「第二套」的 dashboard、gateway、CLI、auth，只要带 **`-p instance2`**（或 `HERMES_HOME` 指向该目录），读写的都是 **该目录下的树**；与默认 `~/.hermes` **不是同一套文件**。

---

## 二、跨实例共享或「同一物理资源」的部分

| 类别 | 共享方式 | 注意 |
|------|-----------|------|
| **Hermes 程序本体** | 同一 Python 解释器 / venv、`hermes` 入口、`site-packages` | 版本一致；升级一次，所有 profile 用的都是同一份安装包（除非多套 venv） |
| **本仓库代码与内置插件** | `hermes-agent` 仓库下的 `plugins/`、`skills/` 等随安装/检出共享 | 内置能力版本一致；`PluginManager` 仍会扫描仓库内 bundled 插件 |
| **Profile 注册表所在盘区** | 命名 profile 的父目录一般为 `~/.hermes/profiles/` | 仅「目录树」上的邻居关系；**各子目录数据仍隔离** |
| **Sticky 当前 profile** | 文件 `~/.hermes/active_profile`（默认根下） | 全局只有一个「默认选中哪个 profile」的指针；**不等于**把两套数据合并 |
| **`hermes profile list`** | 在默认根 `~/.hermes` 下枚举 `profiles/*` | 用于看见所有 profile；各 profile 的 gateway 状态在此列表中展示 |
| **本机网络与端口** | 同一 localhost / 公网 IP | **端口不能重复绑定**：例如两套都开 `api_server` 时，需在各自 `config` / `.env` 中区分端口；dashboard 默认 `9119` 也需错开 |
| **同一即时消息 Bot** | 若两套 `.env` 使用**相同** Telegram/Discord 等 token 且**同时**在线 | 会争用连接；应不同 bot，或只在一套 profile 启用该平台（参见网关适配器与 token lock 相关说明） |
| **项目级插件（可选）** | 启用 `HERMES_ENABLE_PROJECT_PLUGINS` 时，`./.hermes/plugins/`（相对**当前工作目录 cwd**） | 从同一 repo 目录启动时，**不同 profile 可能扫到同一物理目录**；与「每 profile 的 `HERMES_HOME/plugins`」不同 |

**`hermes update`：** 更新的是**仓库/安装树**；各 profile 的 `config.yaml` 版本字段可能随迁移逻辑各自演进，但**代码与内置资源**为共享安装（参见 `AGENTS.md` 中关于多 profile 与 update 的说明）。

---

## 三、运行时建议（两套同时开）

1. **Gateway：** `hermes -p <profile> gateway start`；第二套的 HTTP 能力（如 `api_server`）使用**不同端口**（例如第一套 `8642`、第二套 `8643`）。  
2. **Dashboard：** `hermes dashboard` 与 `hermes -p instance2 dashboard --port <其它端口>`，避免默认 **9119** 冲突。  
3. **密钥：** `--clone` 会复制 `.env`，得到**两份文件**；内容可能相同，但**作用域仅限各自 `HERMES_HOME`**。若希望第二套用不同 Key，只改第二套目录下的 `.env` 即可。

---

## 四、一句话对照

| 问法 | 答案 |
|------|------|
| 会话、记忆、配置是否两套各有一份？ | **是**，按 `HERMES_HOME` 隔离。 |
| 代码、内置插件、Python 包是否两套共用？ | **是**，同一安装/检出。 |
| 端口、Bot token 能否两套完全一样同时跑？ | **端口不能**重复监听；**同一 Bot 多进程**通常**不应**同时挂在两套 gateway 上。 |
| `~/.hermes/plugins` 在 profile 下是哪？ | 命名 profile 为 **`~/.hermes/profiles/<name>/plugins`**，与默认的 **`~/.hermes/plugins`** 不是同一路径。 |

---

## 五、延伸阅读

- 开发与路径约定：`AGENTS.md` 中 **Profiles: Multi-Instance Support**、**Profile-safe code**。  
- 创建与克隆 profile：`hermes_cli/profiles.py` 模块注释与 `hermes profile create --help`。
