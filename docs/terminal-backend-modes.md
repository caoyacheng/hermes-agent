---
title: Terminal Backend Modes
description: terminal.backend / TERMINAL_ENV 六种执行环境说明、选型与安全等级对照
---

# Terminal 执行环境（`terminal.backend`）

`terminal` 工具在沙箱中执行 shell 命令。`terminal.backend`（以及桥接后的环境变量 `TERMINAL_ENV`）决定**命令实际跑在哪里**：本机、本机容器、远程 SSH 或云端沙箱。

权威工厂逻辑：[`tools/terminal_tool.py`](../tools/terminal_tool.py) 中的 `_create_environment()`。每种模式对应 `tools/environments/` 下的一个（或 Modal 下的两个）具体实现类，均继承 [`BaseEnvironment`](../tools/environments/base.py)。

## 配置方式

| 来源 | 说明 |
| --- | --- |
| **`config.yaml`** | `terminal.backend: <mode>`（默认 `local`）。见 [`hermes_cli/config.py`](../hermes_cli/config.py) 中 `DEFAULT_CONFIG["terminal"]`。 |
| **环境变量** | 网关等进程常把配置桥接到 `TERMINAL_ENV`，与 `terminal.backend` 语义一致（参见仓库说明「Working directory」与 terminal 小节）。 |

合法取值（非法值会在校验时报错并列出允许列表）：

`local`、`docker`、`singularity`、`modal`、`daytona`、`ssh`

## 六种模式一览

| 取值 | 实现类 | 源文件 |
| --- | --- | --- |
| `local` | `LocalEnvironment` | [`tools/environments/local.py`](../tools/environments/local.py) |
| `docker` | `DockerEnvironment` | [`tools/environments/docker.py`](../tools/environments/docker.py) |
| `singularity` | `SingularityEnvironment` | [`tools/environments/singularity.py`](../tools/environments/singularity.py) |
| `modal` | `ModalEnvironment` 或 `ManagedModalEnvironment` | [`tools/environments/modal.py`](../tools/environments/modal.py)、[`managed_modal.py`](../tools/environments/managed_modal.py) |
| `daytona` | `DaytonaEnvironment` | [`tools/environments/daytona.py`](../tools/environments/daytona.py) |
| `ssh` | `SSHEnvironment` | [`tools/environments/ssh.py`](../tools/environments/ssh.py) |

---

## `local`（本机）

**含义：** 在本机进程里执行命令（默认路径）。

**适合：** 日常开发、调试、构建；需要最低延迟；依赖已安装在宿主上的工具。

**注意：** 隔离性弱于容器——命令直接影响真实操作系统与文件系统；实现上会屏蔽一批提供商/API 密钥相关环境变量向子进程泄漏，但仍不等于完整沙箱。

---

## `docker`（本机 Docker）

**含义：** 在 Docker 容器内执行；实现侧重安全加固（如 cap-drop、资源限额）与可选持久化。

**适合：** 需要与宿主隔离的可重复环境；不信任或实验性命令希望关在容器里。

**注意：** 依赖本机 Docker；有镜像拉取与启动开销。开启把宿主目录挂入容器（如 `terminal.docker_mount_cwd_to_workspace`）会削弱隔离，需自觉权衡。

---

## `singularity`（Singularity / Apptainer）

**含义：** 使用集群常见的 Singularity/Apptainer 运行时（优先探测 `apptainer`，否则 `singularity`）。

**适合：** **HPC/集群**等不允许或未部署 Docker、但允许容器运行时的场景。

**注意：** 依赖对应 CLI；运维模型与镜像习惯偏科研/HPC，通用桌面开发不如 Docker 普遍。

---

## `modal`（Modal 云端）

**含义：** 使用 Modal SDK 在云上创建沙箱执行（`Sandbox.create` / `exec` 等路径）。

**两种实现（由 `terminal.modal_mode` 等解析）：**

- **直连（direct）：** `ModalEnvironment` — 使用本机配置的 Modal 凭据。
- **托管（managed）：** `ManagedModalEnvironment` — 通过托管工具网关执行（可用性与订阅策略见运行时日志与 [`terminal_tool.py`](../tools/terminal_tool.py) 中的报错文案）。

**适合：** 希望弹性云上算力、已有 Modal 账号与工作流。

**注意：** 依赖网络、`modal` 包与有效凭据或托管网关；冷启动与计费由 Modal/服务商侧决定。

---

## `daytona`（Daytona 云端）

**含义：** 使用 Daytona Python SDK 在云端沙箱中执行。

**适合：** 选用 Daytona 作为托管执行后端而非 Modal 的场景。

**注意：** 需要 `DAYTONA_API_KEY` 与 `daytona` SDK；实现中对磁盘等资源存在平台上限（例如磁盘请求可能被上限裁剪）；同样有延迟与供应商锁定因素。

---

## `ssh`（远程主机）

**含义：** 通过 SSH 在远端机上执行；使用 ControlMaster 复用连接，并与会话快照/FileSync 等机制配合同步远端 `~/.hermes` 等相关文件。

**适合：** 命令必须在指定远程机器执行（GPU 工作站、内网服务器等）。

**注意：** 必须配置 `terminal.ssh_host`、`terminal.ssh_user`（及密钥等）；受网络延迟与远端环境稳定性影响；SSH 控制路径在部分平台上有 Unix socket 路径长度等边界条件（实现中有哈希缩短 sock 路径的处理）。

---

## 安全等级评估

下表是对六种后端的**相对比较**（非认证评级、也非渗透结论），便于按威胁模型选型。**维度不同不可简单横向比谁「更安全」**：例如云端执行保护了你的笔记本，但引入了对供应商的信任；本地容器强化主机隔离，却仍与用户内核相邻。

### 评估维度

| 维度 | 含义 |
| --- | --- |
| **对本机宿主机的防护** | 在「笔记本电脑 / 跑 Hermes 的服务器」上，恶意或失控命令能否轻易读写用户目录、窃取密钥、破坏系统。（此处「本机」指 Hermes 进程所在主机。） |
| **隔离边界强度** | 执行环境与宿主 OS / 用户空间的分离程度（命名空间、容器、远端机器、云端 VM）。 |
| **新增信任锚点** | 除 Hermes 自身外，是否依赖 Docker 守护进程、集群运行时、SSH、第三方云 API、镜像仓库等。 |

### 六种模式对照（概括）

表中等级均为**同类对比下的定性档位**，同一档内仍有细微差别。

| 模式 | 对本机宿主防护（默认配置倾向） | 隔离边界（概括） | 主要残留风险 / 降格因素 |
| --- | --- | --- | --- |
| **`local`** | **弱**：命令即以当前用户在宿主上执行 | 无额外隔离层 | 等同交互 shell；虽有 env blocklist，仍不是沙箱；误删与恶意脚本直接影响真实磁盘与进程 |
| **`docker`** | **强到中**：默认路径命令在容器内 | Linux 容器（与用户进程隔离） | 与宿主 **共享内核**（逃逸类 CVE 理论上存在）；**挂载宿主目录**（如 `docker_volumes`、`docker_mount_cwd_to_workspace`）会显著削弱隔离；错误配置 `docker.sock` 等会扩大攻击面 |
| **`singularity`** | **强到中**：与 Docker 同类思路 | Apptainer/Singularity 容器边界 | 同样共享宿主内核；overlay/绑定策略若过宽等同暴露宿主路径 |
| **`modal`** | **对「本机 shell」强**：默认不在笔记本上执行 shell | 供应商侧云端沙箱 | **信任 Modal** 与网络链路；API/计费账户；若向沙箱注入密钥则云上秘密暴露面需自行管控 |
| **`daytona`** | **同上**（执行目标在云端） | 供应商侧云端沙箱 | **信任 Daytona**；`DAYTONA_API_KEY` 保管；数据驻留与合规需按厂商与区域自评 |
| **`ssh`** | **对「本机工作区」强**：shell 在远端 | 远端独立机器的系统边界 | **远端主机**上的数据与权限仍受该 shell 完全影响；SSH 私钥、ControlSocket、被同步的 `~/.hermes` 等若泄露则危及远端与会话 |

**档位归纳（仅作速查）：**

- **对本机磁盘/进程的直接破坏面最小（在配置合理时）：** `modal`、`daytona`、`ssh`（命令不落在 Hermes 所在机的本地 shell；`ssh` 时仍需保护密钥）。
- **本机侧强隔离、无云依赖：** `docker`、`singularity`（优先**不**挂载敏感宿主目录）。
- **隔离最弱、但调试最直：** `local`。

### 使用建议（与威胁模型相关）

1. **执行不可信代码 / 大范围网络拉取**：避免 `local`；优先 **`docker` / `singularity`**（最小挂载），或能接受云厂商时的 **`modal` / `daytona`**。  
2. **仅担心误删本机仓库**：`docker` + 不挂载仓库到可写路径，或使用云端后端。  
3. **合规与数据驻留**：云端模式需查阅供应商条款与区域；**不要把生产密钥无差别注入终端环境变量**（参见各 `docker_env` / 云沙箱惯例）。  
4. **不存在「绝对安全」**：容器与云沙箱均可被错误配置或新型漏洞削弱；最小权限、最小挂载、密钥分级仍是必须。

---

## 相关配置键（节选）

除 `terminal.backend` 外，常见连带项包括：

| 键 | 作用 |
| --- | --- |
| `terminal.cwd` | 工作目录（网关侧常用；桥接到 `TERMINAL_CWD`）。 |
| `terminal.modal_mode` | Modal：`auto` / `direct` / `managed` 等，决定直连或托管。 |
| `terminal.docker_image` / `singularity_image` / `modal_image` / `daytona_image` | 各后端镜像。 |
| `terminal.docker_volumes`、`terminal.docker_mount_cwd_to_workspace` | Docker 挂载与宿主目录映射。 |
| `terminal.container_*` | CPU/内存/磁盘/持久化等（非 local/ssh 时常用）。 |

完整默认值与字段说明见 [`hermes_cli/config.py`](../hermes_cli/config.py) 中 `DEFAULT_CONFIG["terminal"]` 与 Dashboard 配置参考（若已生成）：[`dashboard-config-reference.md`](./dashboard-config-reference.md)。

## 选型简表

| 目标 | 优先考虑 |
| --- | --- |
| 本机快速迭代 | `local` |
| 本机强隔离、固定镜像 | `docker` |
| 仅允许 Apptainer/Singularity 的集群 | `singularity` |
| Modal 云沙箱 | `modal` |
| Daytona 云沙箱 | `daytona` |
| 固定远程一台机器 | `ssh` |
