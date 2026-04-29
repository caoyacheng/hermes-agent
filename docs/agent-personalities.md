---
title: Agent Personalities（人设预设）
description: agent.personalities 内置键说明、中英文释义与用法
---

# Agent Personalities（人设预设）

Hermes 通过 **`agent.personalities`** 提供一组命名的人设：每条是一段 **system 提示叠加层**，配合 **`display.personality`** 或 **`/personality <名字>`** 选用。

- **基底身份**：仍以 **`SOUL.md`**（及默认身份）为主；人设是在其上叠加的语气与角色指令。扩展说明见 [`website/docs/user-guide/features/personality.md`](../website/docs/user-guide/features/personality.md)。
- **代码中的默认值**：内置文案定义在 [`cli.py`](../cli.py) 的 `load_cli_config()` → `defaults["agent"]["personalities"]`（约 366–381 行）；示例副本见 [`cli-config.yaml.example`](../cli-config.yaml.example)。
- **运行时**：选中的人设字符串进入 **`AIAgent.ephemeral_system_prompt`**，在每轮请求中与缓存的主 system 拼接后发往模型（见 [`run_agent.py`](../run_agent.py) 中 “Build the final system message” 注释处）。

## 内置预设一览

下表 **「内置英文摘要」** 对应仓库默认字符串的意图；**「中文释义」** 便于理解与本地化改写（默认产物仍为英文提示词）。

| 键名 | 内置英文摘要 | 中文释义 |
| --- | --- | --- |
| `helpful` | Friendly, general-purpose assistant | 友善、随和的通用助手。 |
| `concise` | Brief, to-the-point responses | 简洁直奔主题，少说废话。 |
| `technical` | Detailed, accurate technical expert | 技术专家口吻：细致、准确、偏工程向。 |
| `creative` | Outside-the-box, innovative solutions | 创意型：发散思维、点子多。 |
| `teacher` | Patient educator with clear examples | 教师型：耐心、条理清晰、爱举例子。 |
| `kawaii` | Cute expressions (kaomoji), enthusiastic | 日系可爱风：颜文字与符号装饰，语气热情温暖。 |
| `catgirl` | Neko / cat-like speech, playful | 猫娘风：带「nya」、猫系颜文字，顽皮好奇。 |
| `pirate` | Nautical pirate captain, adventurous | 海盗船长腔：航海用语、寻宝式比喻。 |
| `shakespeare` | Bardic prose, dramatic flair | 莎士比亚戏剧腔：华丽句式与戏剧性。 |
| `surfer` | Chill surfer / bro slang | 冲浪Bro腔：松弛、口语化、「超酷」。 |
| `noir` | Hard-boiled detective monologue | 黑色电影侦探腔：阴郁独白、悬疑叙事感。 |
| `uwu` | Baby-talk / uwu meme speak | UwU幼幼语：刻意卖萌、动作描写（如 *nuzzle*）。 |
| `philosopher` | Contemplates meaning — how and why | 哲学家腔：不只答做法，也爱讨论动机与意义。 |
| `hype` | Maximum hype / pumped energy | 热血解说腔：极高能量、像在呐喊助威。 |

## 用法

### CLI / TUI

```text
/personality
/personality kawaii
/personality none
```

### 配置文件

在 **`~/.hermes/config.yaml`**（或当前 profile 的 `config.yaml`）中：

```yaml
display:
  personality: kawaii   # 当前选用的预设名

agent:
  personalities:
    # 可覆盖或新增键；以下为「中文人设」示例（需自测模型是否稳定遵循中文）
    helpful: "你是一个友善、随和的助手，用中文清晰回答。"
```

若 **`agent.personalities`** 被清空且未合并回内置表，仅设置 **`display.personality`** 可能无法解析名字；此时应保留或补全 `agent.personalities` 条目，参见 [`tui_gateway/server.py`](../tui_gateway/server.py) 中 `_validate_personality` 与健康检查逻辑。

## 与 `cli-config.yaml.example` 的关系

仓库根目录下的 **`cli-config.yaml.example`** 中的 `agent.personalities` 区块与 **`cli.py` 内建 defaults** 对齐，供复制到自有配置；**运行时以合并后的有效配置为准**，而非单独读取 `.example` 文件。
