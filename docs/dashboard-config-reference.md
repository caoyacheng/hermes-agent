---
title: Dashboard Config Reference
description: Web Dashboard 配置页字段说明（自动生成）
---

# Dashboard 配置字段说明

这份文档对应 Web Dashboard 的 **配置** 页面字段。字段来源于后端 `CONFIG_SCHEMA`（由 `DEFAULT_CONFIG` 自动展开生成）。

## 生成方式

如需刷新此文档：

```bash
python scripts/generate_dashboard_config_docs.py > docs/dashboard-config-reference.md
```

## 分类概览

| Category | 字段数 |
| --- | ---: |
| `general` | 9 |
| `agent` | 25 |
| `terminal` | 19 |
| `display` | 20 |
| `delegation` | 12 |
| `memory` | 5 |
| `compression` | 4 |
| `security` | 13 |
| `browser` | 9 |
| `voice` | 6 |
| `tts` | 16 |
| `stt` | 6 |
| `logging` | 3 |
| `discord` | 6 |
| `auxiliary` | 42 |
| `bedrock` | 8 |
| `model_catalog` | 3 |
| `prompt_caching` | 1 |
| `sessions` | 4 |
| `tool_output` | 3 |
| `updates` | 2 |

## general

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `command_allowlist` | `list` | `[]` | 用途：Command Allowlist。 |
| `fallback_providers` | `list` | `[]` | 用途：Fallback Providers。 |
| `file_read_max_chars` | `number` | `100000` | 用途：File Read Max Chars。 |
| `hooks_auto_accept` | `boolean` | `false` | 用途：Hooks Auto Accept。 |
| `model` | `string` | `""` | 默认使用的模型 ID（例如 anthropic/claude-sonnet-4.6）。 |
| `model_context_length` | `number` | `0` | 上下文窗口覆盖值（0 表示自动从模型元数据探测）。 |
| `prefill_messages_file` | `string` | `""` | 用途：Prefill Messages File。 |
| `timezone` | `string` | `""` | 用途：Timezone。 |
| `toolsets` | `list` | `["hermes-cli"]` | 用途：Toolsets。 |

## agent

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `agent.api_max_retries` | `number` | `3` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.gateway_notify_interval` | `number` | `180` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.gateway_timeout` | `number` | `1800` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.gateway_timeout_warning` | `number` | `900` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.image_input_mode` | `string` | `"auto"` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.max_turns` | `number` | `90` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.restart_drain_timeout` | `number` | `60` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.service_tier` | `select` | `""` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `agent.tool_use_enforcement` | `string` | `"auto"` | Agent 行为相关参数（循环上限、超时、重启/恢复策略等）。 |
| `checkpoints.auto_prune` | `boolean` | `false` | 用途：Checkpoints → Auto Prune。 |
| `checkpoints.delete_orphans` | `boolean` | `true` | 用途：Checkpoints → Delete Orphans。 |
| `checkpoints.enabled` | `boolean` | `true` | 用途：Checkpoints → Enabled。 |
| `checkpoints.max_snapshots` | `number` | `50` | 用途：Checkpoints → Max Snapshots。 |
| `checkpoints.min_interval_hours` | `number` | `24` | 用途：Checkpoints → Min Interval Hours。 |
| `checkpoints.retention_days` | `number` | `7` | 用途：Checkpoints → Retention Days。 |
| `code_execution.mode` | `string` | `"project"` | 用途：Code Execution → Mode。 |
| `context.engine` | `select` | `"compressor"` | 用途：Context management engine。 |
| `cron.max_parallel_jobs` | `string` | `null` | 用途：Cron → Max Parallel Jobs。 |
| `cron.wrap_response` | `boolean` | `true` | 用途：Cron → Wrap Response。 |
| `network.force_ipv4` | `boolean` | `false` | 用途：Network → Force Ipv4。 |
| `skills.external_dirs` | `list` | `[]` | 用途：Skills → External Dirs。 |
| `skills.guard_agent_created` | `boolean` | `false` | 用途：Skills → Guard Agent Created。 |
| `skills.inline_shell` | `boolean` | `false` | 用途：Skills → Inline Shell。 |
| `skills.inline_shell_timeout` | `number` | `10` | 用途：Skills → Inline Shell Timeout。 |
| `skills.template_vars` | `boolean` | `true` | 用途：Skills → Template Vars。 |

## terminal

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `terminal.auto_source_bashrc` | `boolean` | `true` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.backend` | `select` | `"local"` | 命令执行后端（本机/容器/远程等），影响 terminal 工具的运行环境。 |
| `terminal.container_cpu` | `number` | `1` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.container_disk` | `number` | `51200` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.container_memory` | `number` | `5120` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.container_persistent` | `boolean` | `true` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.cwd` | `string` | `"."` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.daytona_image` | `string` | `"nikolaik/python-nodejs:python3.11-nodejs20"` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.docker_forward_env` | `list` | `[]` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.docker_image` | `string` | `"nikolaik/python-nodejs:python3.11-nodejs20"` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.docker_mount_cwd_to_workspace` | `boolean` | `false` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.docker_volumes` | `list` | `[]` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.env_passthrough` | `list` | `[]` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.modal_image` | `string` | `"nikolaik/python-nodejs:python3.11-nodejs20"` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.modal_mode` | `select` | `"auto"` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.persistent_shell` | `boolean` | `true` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.shell_init_files` | `list` | `[]` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.singularity_image` | `string` | `"docker://nikolaik/python-nodejs:python3.11-nodejs20"` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |
| `terminal.timeout` | `number` | `180` | 终端/执行环境相关参数（backend、超时、工作目录、沙箱与资源限制等）。 |

## display

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `dashboard.theme` | `select` | `"default"` | Web Dashboard 主题。 |
| `display.bell_on_complete` | `boolean` | `false` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.busy_input_mode` | `select` | `"interrupt"` | Agent 运行时你在 UI 输入的处理方式（中断/排队/steer）。 |
| `display.compact` | `boolean` | `false` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.final_response_markdown` | `string` | `"strip"` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.inline_diffs` | `boolean` | `true` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.interim_assistant_messages` | `boolean` | `true` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.personality` | `string` | `"kawaii"` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.resume_display` | `select` | `"full"` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.show_cost` | `boolean` | `false` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.show_reasoning` | `boolean` | `false` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.skin` | `select` | `"default"` | CLI 主题皮肤（影响终端界面配色/品牌文案/Spinner 等）。 |
| `display.streaming` | `boolean` | `false` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.tool_preview_length` | `number` | `0` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.tool_progress_command` | `boolean` | `false` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.user_message_preview.first_lines` | `number` | `2` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `display.user_message_preview.last_lines` | `number` | `2` | 交互展示相关参数（UI 风格、输出展示、输入行为、提示/进度等）。 |
| `human_delay.max_ms` | `number` | `2500` | 用途：Human Delay → Max Ms。 |
| `human_delay.min_ms` | `number` | `800` | 用途：Human Delay → Min Ms。 |
| `human_delay.mode` | `select` | `"off"` | 用途：Simulated typing delay mode。 |

## delegation

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `delegation.api_key` | `string` | `""` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.base_url` | `string` | `""` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.child_timeout_seconds` | `number` | `600` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.inherit_mcp_toolsets` | `boolean` | `true` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.max_concurrent_children` | `number` | `3` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.max_iterations` | `number` | `50` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.max_spawn_depth` | `number` | `1` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.model` | `string` | `""` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.orchestrator_enabled` | `boolean` | `true` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.provider` | `string` | `""` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.reasoning_effort` | `select` | `""` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |
| `delegation.subagent_auto_approve` | `boolean` | `false` | 子代理/委托相关参数（并发、推理强度、隔离策略、超时等）。 |

## memory

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `memory.memory_char_limit` | `number` | `2200` | 记忆系统相关参数（provider、注入策略、同步/召回等）。 |
| `memory.memory_enabled` | `boolean` | `true` | 记忆系统相关参数（provider、注入策略、同步/召回等）。 |
| `memory.provider` | `select` | `""` | 记忆系统相关参数（provider、注入策略、同步/召回等）。 |
| `memory.user_char_limit` | `number` | `1375` | 记忆系统相关参数（provider、注入策略、同步/召回等）。 |
| `memory.user_profile_enabled` | `boolean` | `true` | 记忆系统相关参数（provider、注入策略、同步/召回等）。 |

## compression

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `compression.enabled` | `boolean` | `true` | 上下文压缩/上下文工程相关参数（阈值、策略、预算等）。 |
| `compression.protect_last_n` | `number` | `20` | 上下文压缩/上下文工程相关参数（阈值、策略、预算等）。 |
| `compression.target_ratio` | `number` | `0.2` | 上下文压缩/上下文工程相关参数（阈值、策略、预算等）。 |
| `compression.threshold` | `number` | `0.5` | 上下文压缩/上下文工程相关参数（阈值、策略、预算等）。 |

## security

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `approvals.cron_mode` | `string` | `"deny"` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `approvals.mode` | `select` | `"manual"` | 危险命令审批模式（询问/放行/拒绝）。 |
| `approvals.timeout` | `number` | `60` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `privacy.redact_pii` | `boolean` | `false` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.allow_private_urls` | `boolean` | `false` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.redact_secrets` | `boolean` | `false` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.tirith_enabled` | `boolean` | `true` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.tirith_fail_open` | `boolean` | `true` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.tirith_path` | `string` | `"tirith"` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.tirith_timeout` | `number` | `5` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.website_blocklist.domains` | `list` | `[]` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.website_blocklist.enabled` | `boolean` | `false` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |
| `security.website_blocklist.shared_files` | `list` | `[]` | 安全与权限相关参数（URL 安全、命令审批、访问控制等）。 |

## browser

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `browser.allow_private_urls` | `boolean` | `false` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.auto_local_for_private_urls` | `boolean` | `true` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.camofox.managed_persistence` | `boolean` | `false` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.cdp_url` | `string` | `""` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.command_timeout` | `number` | `30` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.dialog_policy` | `string` | `"must_respond"` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.dialog_timeout_s` | `number` | `300` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.inactivity_timeout` | `number` | `120` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |
| `browser.record_sessions` | `boolean` | `false` | 浏览器/爬取相关参数（会话超时、连接、后端等）。 |

## voice

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `voice.auto_tts` | `boolean` | `false` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `voice.beep_enabled` | `boolean` | `true` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `voice.max_recording_seconds` | `number` | `120` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `voice.record_key` | `string` | `"ctrl+b"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `voice.silence_duration` | `number` | `3.0` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `voice.silence_threshold` | `number` | `200` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |

## tts

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `tts.edge.voice` | `string` | `"en-US-AriaNeural"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.elevenlabs.model_id` | `string` | `"eleven_multilingual_v2"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.elevenlabs.voice_id` | `string` | `"pNInz6obpgDQGcFmaJgB"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.mistral.model` | `string` | `"voxtral-mini-tts-2603"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.mistral.voice_id` | `string` | `"c69964a6-ab8b-4f8a-9465-ec0925096ec8"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.neutts.device` | `string` | `"cpu"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.neutts.model` | `string` | `"neuphonic/neutts-air-q4-gguf"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.neutts.ref_audio` | `string` | `""` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.neutts.ref_text` | `string` | `""` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.openai.model` | `string` | `"gpt-4o-mini-tts"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.openai.voice` | `string` | `"alloy"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.provider` | `select` | `"edge"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.xai.bit_rate` | `number` | `128000` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.xai.language` | `string` | `"en"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.xai.sample_rate` | `number` | `24000` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `tts.xai.voice_id` | `string` | `"eve"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |

## stt

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `stt.enabled` | `boolean` | `true` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `stt.local.language` | `string` | `""` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `stt.local.model` | `string` | `"base"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `stt.mistral.model` | `string` | `"voxtral-mini-latest"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `stt.openai.model` | `string` | `"whisper-1"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |
| `stt.provider` | `select` | `"local"` | 语音相关参数（TTS/STT provider、模型、长度/质量限制等）。 |

## logging

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `logging.backup_count` | `number` | `3` | 日志相关参数（级别、落盘与展示行为等）。 |
| `logging.level` | `select` | `"INFO"` | 日志相关参数（级别、落盘与展示行为等）。 |
| `logging.max_size_mb` | `number` | `5` | 日志相关参数（级别、落盘与展示行为等）。 |

## discord

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `discord.allowed_channels` | `string` | `""` | 消息平台相关参数（授权、频道/群策略、行为开关等）。 |
| `discord.auto_thread` | `boolean` | `true` | 消息平台相关参数（授权、频道/群策略、行为开关等）。 |
| `discord.free_response_channels` | `string` | `""` | 消息平台相关参数（授权、频道/群策略、行为开关等）。 |
| `discord.reactions` | `boolean` | `true` | 消息平台相关参数（授权、频道/群策略、行为开关等）。 |
| `discord.require_mention` | `boolean` | `true` | 消息平台相关参数（授权、频道/群策略、行为开关等）。 |
| `discord.server_actions` | `string` | `""` | 消息平台相关参数（授权、频道/群策略、行为开关等）。 |

## auxiliary

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `auxiliary.approval.api_key` | `string` | `""` | 用途：Auxiliary → Approval → Api Key。 |
| `auxiliary.approval.base_url` | `string` | `""` | 用途：Auxiliary → Approval → Base Url。 |
| `auxiliary.approval.model` | `string` | `""` | 用途：Auxiliary → Approval → Model。 |
| `auxiliary.approval.provider` | `string` | `"auto"` | 用途：Auxiliary → Approval → Provider。 |
| `auxiliary.approval.timeout` | `number` | `30` | 用途：Auxiliary → Approval → Timeout。 |
| `auxiliary.compression.api_key` | `string` | `""` | 用途：Auxiliary → Compression → Api Key。 |
| `auxiliary.compression.base_url` | `string` | `""` | 用途：Auxiliary → Compression → Base Url。 |
| `auxiliary.compression.model` | `string` | `""` | 用途：Auxiliary → Compression → Model。 |
| `auxiliary.compression.provider` | `string` | `"auto"` | 用途：Auxiliary → Compression → Provider。 |
| `auxiliary.compression.timeout` | `number` | `120` | 用途：Auxiliary → Compression → Timeout。 |
| `auxiliary.mcp.api_key` | `string` | `""` | 用途：Auxiliary → Mcp → Api Key。 |
| `auxiliary.mcp.base_url` | `string` | `""` | 用途：Auxiliary → Mcp → Base Url。 |
| `auxiliary.mcp.model` | `string` | `""` | 用途：Auxiliary → Mcp → Model。 |
| `auxiliary.mcp.provider` | `string` | `"auto"` | 用途：Auxiliary → Mcp → Provider。 |
| `auxiliary.mcp.timeout` | `number` | `30` | 用途：Auxiliary → Mcp → Timeout。 |
| `auxiliary.session_search.api_key` | `string` | `""` | 用途：Auxiliary → Session Search → Api Key。 |
| `auxiliary.session_search.base_url` | `string` | `""` | 用途：Auxiliary → Session Search → Base Url。 |
| `auxiliary.session_search.max_concurrency` | `number` | `3` | 用途：Auxiliary → Session Search → Max Concurrency。 |
| `auxiliary.session_search.model` | `string` | `""` | 用途：Auxiliary → Session Search → Model。 |
| `auxiliary.session_search.provider` | `string` | `"auto"` | 用途：Auxiliary → Session Search → Provider。 |
| `auxiliary.session_search.timeout` | `number` | `30` | 用途：Auxiliary → Session Search → Timeout。 |
| `auxiliary.skills_hub.api_key` | `string` | `""` | 用途：Auxiliary → Skills Hub → Api Key。 |
| `auxiliary.skills_hub.base_url` | `string` | `""` | 用途：Auxiliary → Skills Hub → Base Url。 |
| `auxiliary.skills_hub.model` | `string` | `""` | 用途：Auxiliary → Skills Hub → Model。 |
| `auxiliary.skills_hub.provider` | `string` | `"auto"` | 用途：Auxiliary → Skills Hub → Provider。 |
| `auxiliary.skills_hub.timeout` | `number` | `30` | 用途：Auxiliary → Skills Hub → Timeout。 |
| `auxiliary.title_generation.api_key` | `string` | `""` | 用途：Auxiliary → Title Generation → Api Key。 |
| `auxiliary.title_generation.base_url` | `string` | `""` | 用途：Auxiliary → Title Generation → Base Url。 |
| `auxiliary.title_generation.model` | `string` | `""` | 用途：Auxiliary → Title Generation → Model。 |
| `auxiliary.title_generation.provider` | `string` | `"auto"` | 用途：Auxiliary → Title Generation → Provider。 |
| `auxiliary.title_generation.timeout` | `number` | `30` | 用途：Auxiliary → Title Generation → Timeout。 |
| `auxiliary.vision.api_key` | `string` | `""` | 用途：Auxiliary → Vision → Api Key。 |
| `auxiliary.vision.base_url` | `string` | `""` | 用途：Auxiliary → Vision → Base Url。 |
| `auxiliary.vision.download_timeout` | `number` | `30` | 用途：Auxiliary → Vision → Download Timeout。 |
| `auxiliary.vision.model` | `string` | `""` | 用途：Auxiliary → Vision → Model。 |
| `auxiliary.vision.provider` | `string` | `"auto"` | 用途：Auxiliary → Vision → Provider。 |
| `auxiliary.vision.timeout` | `number` | `120` | 用途：Auxiliary → Vision → Timeout。 |
| `auxiliary.web_extract.api_key` | `string` | `""` | 用途：Auxiliary → Web Extract → Api Key。 |
| `auxiliary.web_extract.base_url` | `string` | `""` | 用途：Auxiliary → Web Extract → Base Url。 |
| `auxiliary.web_extract.model` | `string` | `""` | 用途：Auxiliary → Web Extract → Model。 |
| `auxiliary.web_extract.provider` | `string` | `"auto"` | 用途：Auxiliary → Web Extract → Provider。 |
| `auxiliary.web_extract.timeout` | `number` | `360` | 用途：Auxiliary → Web Extract → Timeout。 |

## bedrock

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `bedrock.discovery.enabled` | `boolean` | `true` | 用途：Bedrock → Discovery → Enabled。 |
| `bedrock.discovery.provider_filter` | `list` | `[]` | 用途：Bedrock → Discovery → Provider Filter。 |
| `bedrock.discovery.refresh_interval` | `number` | `3600` | 用途：Bedrock → Discovery → Refresh Interval。 |
| `bedrock.guardrail.guardrail_identifier` | `string` | `""` | 用途：Bedrock → Guardrail → Guardrail Identifier。 |
| `bedrock.guardrail.guardrail_version` | `string` | `""` | 用途：Bedrock → Guardrail → Guardrail Version。 |
| `bedrock.guardrail.stream_processing_mode` | `string` | `"async"` | 用途：Bedrock → Guardrail → Stream Processing Mode。 |
| `bedrock.guardrail.trace` | `string` | `"disabled"` | 用途：Bedrock → Guardrail → Trace。 |
| `bedrock.region` | `string` | `""` | 用途：Bedrock → Region。 |

## model_catalog

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `model_catalog.enabled` | `boolean` | `true` | 用途：Model Catalog → Enabled。 |
| `model_catalog.ttl_hours` | `number` | `24` | 用途：Model Catalog → Ttl Hours。 |
| `model_catalog.url` | `string` | `"https://hermes-agent.nousresearch.com/docs/api/model-catalog.json"` | 用途：Model Catalog → Url。 |

## prompt_caching

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `prompt_caching.cache_ttl` | `string` | `"5m"` | 用途：Prompt Caching → Cache Ttl。 |

## sessions

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `sessions.auto_prune` | `boolean` | `false` | 用途：Sessions → Auto Prune。 |
| `sessions.min_interval_hours` | `number` | `24` | 用途：Sessions → Min Interval Hours。 |
| `sessions.retention_days` | `number` | `90` | 用途：Sessions → Retention Days。 |
| `sessions.vacuum_after_prune` | `boolean` | `true` | 用途：Sessions → Vacuum After Prune。 |

## tool_output

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `tool_output.max_bytes` | `number` | `50000` | 用途：Tool Output → Max Bytes。 |
| `tool_output.max_line_length` | `number` | `2000` | 用途：Tool Output → Max Line Length。 |
| `tool_output.max_lines` | `number` | `2000` | 用途：Tool Output → Max Lines。 |

## updates

| Key | Type | Default | 用途 |
| --- | --- | --- | --- |
| `updates.backup_keep` | `number` | `5` | 用途：Updates → Backup Keep。 |
| `updates.pre_update_backup` | `boolean` | `false` | 用途：Updates → Pre Update Backup。 |

