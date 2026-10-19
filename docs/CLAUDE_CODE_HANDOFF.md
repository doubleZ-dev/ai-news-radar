# Maker Inspiration Radar：Claude Code 转交文档

> 更新时间：2026-10-19（Asia/Shanghai）  
> 当前分支：`maker-radar`  
> 当前提交：`23f68728 feat: expand stable maker source coverage`

## 1. 项目目标

本项目由 `LearnPrompt/ai-news-radar` fork 而来，正在改造成面向独立创客的
“Maker Inspiration Radar / 创客灵感雷达”。

它不是普通新闻摘要工具。目标流程是：

```text
公开信息源采集
→ 保留全部原始候选和链接
→ 去重与逐条判断
→ 每天精选 5–8 条创客机会
→ 给出具体项目想法和最低成本验证方法
→ 写入 Obsidian
→ 只进入 Idea Bank，不自动启动新项目
```

用户背景和优先方向：

- 电子 DIY、ESP32、传感器、嵌入式设备
- 机器人、桌面交互装置、机械结构
- 3D 打印、新材料、开源硬件
- AI 编程、软硬件交互
- 创意玩具、解压装置、可拍视频的实体效果
- 可开源、制作套件或探索商业化的项目
- MakerWorld、Hackaday、YouTube 创客频道等创客信号，优先于一般 AI 融资新闻

每条候选使用两个独立评分：

- 热度评分 `0–5`：只能依据可核实指标；缺数据必须是 `null/未知`
- 创客匹配评分 `0–5`：实现难度、视觉表现、成本、周期、技能匹配、传播和商业潜力

高创客匹配、低热度的项目允许入选。

## 2. 项目地址

### 本地与 GitHub

- 本地仓库：`F:\Documents\信息获取`
- 用户 fork：<https://github.com/doubleZ-dev/ai-news-radar>
- fork 远端：`origin`
- 上游仓库：<https://github.com/LearnPrompt/ai-news-radar>
- 上游远端：`upstream`
- 开发分支：`maker-radar`
- 最新已推送提交：`23f68728`

开始工作前：

```powershell
Set-Location "F:\Documents\信息获取"
git checkout maker-radar
git pull origin maker-radar
```

不要点击 GitHub 的 `Compare & pull request` 去向原上游提交，除非用户以后明确想把改动贡献给
`LearnPrompt/ai-news-radar`。

### Obsidian 输出

Obsidian 根目录如下。`apple note` 中间是一个特殊的窄空格 `U+2006`，不要手工改成普通空格：

```text
C:\Users\zengzhi\iCloudDrive\iCloud~md~obsidian\apple note\每日热点
```

每天创建 `YYYYMMDD` 子目录，并写入：

```text
YYYY-MM-DD-每日精选.md
YYYY-MM-DD-全部发现.md
```

今天已有：

```text
C:\Users\zengzhi\iCloudDrive\iCloud~md~obsidian\apple note\每日热点\20261019\2026-10-19-每日精选.md
C:\Users\zengzhi\iCloudDrive\iCloud~md~obsidian\apple note\每日热点\20261019\2026-10-19-全部发现.md
```

今天现有文档是扩源前一轮生成的：精选 8 条，完整候选 57 条。最后一次扩源实跑得到
95 条候选，但只是验证运行，没有覆盖今天的 Obsidian 文档，也没有保留临时 JSON。

## 3. 必须先阅读的文件

Claude Code 接手后依次阅读：

1. `AGENTS.md`
2. `skills/ai-news-radar/SKILL.md`
3. `docs/CLAUDE_CODE_HANDOFF.md`（本文）
4. `docs/MAKER_RADAR_MVP.md`
5. `docs/MAKER_SOURCE_STATUS.md`
6. `docs/SOURCE_COVERAGE.md`
7. `config/maker-sources.json`
8. `prompts/maker-opportunity-analysis.md`

仓库规则重点：

- 优先官方 RSS/Atom、公开 JSON API 和公开 GitHub 生成 Feed
- 不提交 API Key、Cookie、Token、`.env` 或真实私人 OPML
- 不把失败、跳过或零权限伪装成已扫描成功
- 修改来源前先查看当前来源覆盖和现有解析器
- 文件修改保持小而可审查

## 4. 当前完成情况

### 核心工作流

已完成：

- 原始候选统一结构
- 每个来源独立状态：健康、跳过、失败、候选数、错误原因
- 原始链接和采集证据保留
- 热度与创客匹配分离
- 每日最多精选 8 条
- 每个原始候选必须有明确入选或未入选决定
- “事实 / 社区观点 / AI 推测 / 风险”分开记录
- 生成“每日精选”和“全部发现”两份 Markdown
- 自动按日期创建 Obsidian 目录
- 本地 Idea Bank 接口，不自动立项

### 最近一次真实来源验证

2026-10-19 完整实跑结果：

- 健康来源：22
- 明确跳过：11
- 运行失败：0
- 候选：95
- 测试：381 passed（需要 UTF-8 模式）

### 当前健康来源（22）

1. GitHub Trending
2. Hackaday
3. Hacker News
4. 3D Printing Industry
5. Reddit Maker Communities
6. YouTube · Stuff Made Here
7. YouTube · Teaching Tech
8. YouTube · DIY Machines
9. Product Hunt
10. Hugging Face Daily Papers
11. X · Follow Builders
12. Arduino Blog
13. Adafruit Blog
14. Raspberry Pi News
15. SparkFun News
16. Make: Magazine
17. Prusa Blog
18. Bambu Lab Blog
19. CNX Software
20. Seeed Studio Blog
21. arXiv Robotics RSS
22. Hackster Projects Atom

YouTube 三个 Feed 在最近一次采集中均成功解析，但最近 7 天没有新上传，因此是“健康、0 条”，
不是失败。YouTube 已使用专门解析器：按上传时间判断新旧、保留播放量，并对偶发 404 做两次有限重试；
持续失败仍会如实进入来源状态。

### 当前明确跳过的来源（11）

1. Bilibili：公开搜索曾返回 HTTP 412
2. Xiaohongshu：需要 TikHub 等私有 API Key
3. Douyin：需要 TikHub 等私有 API Key
4. TikTok：没有已验证的稳定公开搜索/Feed
5. WeChat Official Accounts：候选聚合端点返回 HTTP 403，且没有账号白名单
6. Crowd Supply：候选 RSS 地址为 404
7. Kickstarter：公开发现页有 TLS/403 挑战
8. Instructables：候选 Feed 跳转登录页
9. Thingiverse：候选 RSS 404，公开 API 路径未验证
10. Printables：页面/候选 Feed 返回 403
11. MakerWorld：直接访问返回 403

这些来源必须继续显示为“跳过”，不可写成“已扫描但没有新内容”。

## 5. 关键文件职责

| 文件 | 作用 |
| --- | --- |
| `config/maker-sources.json` | 创客来源注册表、时间窗口、上限、启用与跳过理由 |
| `scripts/maker_sources.py` | 各类来源解析、标签、热度证据和统一候选结构 |
| `scripts/collect_maker_candidates.py` | 逐来源采集、失败隔离、状态统计、生成原始候选 JSON |
| `prompts/maker-opportunity-analysis.md` | AI 筛选协议与输出 JSON 结构 |
| `scripts/maker_analysis.py` | 检查 95/全部候选是否逐条有决定，防止静默丢失 |
| `scripts/maker_opportunity.py` | 精选排序、去重、Idea Bank 抑制和每日摘要结构 |
| `scripts/render_maker_reports.py` | 生成“每日精选”和“全部发现”Markdown |
| `scripts/idea_bank.py` | 保存、忽略、候选研究等本地反馈动作 |
| `config/maker-radar.json` | 用户能力、兴趣和每日精选数量配置 |
| `docs/MAKER_SOURCE_STATUS.md` | 当前真实来源覆盖和跳过原因 |
| `tests/test_maker_sources.py` | 来源解析、YouTube 时间/热度与失败透明度测试 |

以下文件默认被 `.gitignore` 忽略，因为是本地生成或可能包含个人偏好：

```text
data/maker-candidates.json
data/maker-analysis.json
data/maker-daily.json
data/idea-bank.json
reports/daily/
```

## 6. 当前自动化状态

### Codex 本地定时任务

当前仍有一个 `ACTIVE` 的 Codex 本地自动化：

- ID：`maker-radar`
- 名称：`Maker Radar 每日创客灵感`
- 时间：每天 08:30（Asia/Shanghai）
- 项目：`F:\Documents\信息获取`
- 配置文件：`C:\Users\zengzhi\.codex\automations\maker-radar\automation.toml`
- 模型：`gpt-5.4`

它执行：采集 → AI 逐条筛选 → 校验 → 写入 Obsidian。

重要：如果用户完全转交给 Claude Code，并且不希望继续消耗 Codex 额度，应由用户在 Codex 中暂停或删除
这个自动化。不要在没有用户明确同意时静默删除。

### GitHub Actions

`.github/workflows/update-news.yml` 当前只更新原 AI News Radar 的 `data/*.json`、Persona、RSS 等数据。
它没有运行 Maker Radar 的候选采集、AI 分析和 Obsidian 写入流程。

所以目前每日 Maker Radar 自动化仍依赖 Codex 本地任务，不能声称 GitHub 已接管创客日报。

如果 Claude Code 后续要接管定时运行，优先考虑本地 Windows 任务计划程序或 Claude 自己的计划任务，
因为 Obsidian 位于本机 iCloud Drive，GitHub Actions 无法直接写入该本地目录。

## 7. 本地运行命令

### 安装与测试

已有虚拟环境：

```powershell
Set-Location "F:\Documents\信息获取"
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:PYTHONUTF8
```

最后已验证结果：`381 passed`。

Windows 默认 GBK 会导致仓库部分 UTF-8 测试和控制台输出报错，因此请设置 `PYTHONUTF8=1`。

### 采集原始候选

```powershell
Set-Location "F:\Documents\信息获取"
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe scripts\collect_maker_candidates.py --output data\maker-candidates.json
```

采集结束后检查：

- `total_items`
- `source_status`
- 每个来源的 `ok`、`skipped`、`item_count` 和 `error`
- `info_gaps`

### AI 筛选

严格按照 `prompts/maker-opportunity-analysis.md`：

1. 读取 `data/maker-candidates.json`
2. 打开入选候选的原始链接进行核实
3. 给每个 `discovery_id` 写一条 `decisions`
4. 精选 5–8 条写入 `opportunities`
5. 原样复制 `heat_score` 和 `heat_evidence`
6. 输出合法 JSON 到 `data/maker-analysis.json`

任何一次重新采集都会改变候选集合；旧的分析 JSON 很可能因此失效。不要绕过验证器。

### 写入 Obsidian

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe scripts\render_maker_reports.py `
  --raw data\maker-candidates.json `
  --analysis data\maker-analysis.json `
  --output-dir "C:\Users\zengzhi\iCloudDrive\iCloud~md~obsidian\apple note\每日热点" `
  --dated-subdir
Remove-Item Env:PYTHONUTF8
```

只允许修改当天日期目录中的两份 Maker Radar 文档，不要改动其他 Obsidian 笔记。

## 8. 已知问题和注意事项

1. 当前 95 条候选还没有做新一轮完整 AI 筛选；今天 Obsidian 仍是 57 条版本。
2. YouTube Feed 可偶发 404；代码已有限重试，但失败必须继续透明记录。
3. arXiv 使用官方 `cs.RO` RSS，避免之前 query API 的 429；当前最多保留 10 条。
4. Reddit RSS 没有可靠投票/评论指标，因此热度保持未知。
5. X 只是 Follow Builders 的公开精选快照，不是全 X 扫描。
6. B 站、小红书、抖音、TikTok、公众号等不能依赖登录 Cookie 写入公开仓库。
7. `apple note` 路径包含 U+2006；没有 `PYTHONUTF8=1` 时，报告实际上可能已经写入，但最后打印路径会触发控制台编码错误。
8. 不要提交 `data/maker-analysis.json`、Idea Bank、私有 OPML 或任何密钥。

## 9. 建议下一步

按优先级：

1. 重新采集当前 22 个健康来源，得到约 95 条候选。
2. 完成 95 条逐条决策，更新当天或下一次运行的两份 Obsidian 文档。
3. 增加更活跃的优质 YouTube 创客频道；先核实官方 channel ID，再接入官方 Atom。
4. 研究 MakerWorld/Printables 可长期运行的公开 Feed 或官方 API，不使用脆弱 Cookie 抓取。
5. 为小红书/抖音设计“本地私有 API Key”路径；密钥只放环境变量，不进入 Git。
6. 记录用户在 Idea Bank 中的保存、忽略、候选研究反馈，用于以后调整匹配规则。
7. 用户确认转移完成后，再暂停 Codex 的 `maker-radar` 自动化，避免重复运行和继续消耗额度。

## 10. 可直接复制给 Claude Code 的提示词

```text
你现在接手 Maker Inspiration Radar 项目。

本地仓库：F:\Documents\信息获取
GitHub fork：https://github.com/doubleZ-dev/ai-news-radar
分支：maker-radar

请先完整阅读：
1. AGENTS.md
2. skills/ai-news-radar/SKILL.md
3. docs/CLAUDE_CODE_HANDOFF.md
4. docs/MAKER_RADAR_MVP.md
5. docs/MAKER_SOURCE_STATUS.md
6. docs/SOURCE_COVERAGE.md
7. config/maker-sources.json
8. prompts/maker-opportunity-analysis.md

当前状态：22 个健康来源、11 个明确跳过来源、最近实跑 95 条候选、0 个运行失败。
今天 Obsidian 中仍是上一轮 57 条候选和 8 条精选，新扩展的 95 条还未完成逐条 AI 筛选。

请先执行一次只读检查和 git status，不要大规模重构。然后：
1. 用 PYTHONUTF8=1 运行全仓测试。
2. 重新采集 maker-candidates.json。
3. 检查 source_status，绝不能把失败或跳过写成扫描成功。
4. 严格按 prompts/maker-opportunity-analysis.md 对每个 discovery_id 写入决定，精选 5–8 条。
5. 生成“每日精选”和“全部发现”两份 Markdown 到当天 Obsidian 日期目录。
6. 汇报健康/跳过/失败来源数、候选数、精选数和最值得关注的两个方向。

不要把 API Key、Cookie、Token、私人 OPML、Idea Bank 或分析生成文件提交到 Git。
不要自动立项，不要修改其他 Obsidian 笔记。
```

