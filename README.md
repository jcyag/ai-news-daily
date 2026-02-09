# 🤖 AI资讯日报 (AI News Daily)

全自动、双语、多源、智能的 AI 资讯情报站。每天为您精选 24-48 小时内全球最重要的 AI 动态。

## ✨ 功能特性

- **🌍 多源采集**:
    - **学术前沿**: Hugging Face Papers (带摘要)
    - **技术社区**: Hacker News, Reddit (r/MachineLearning等)
    - **社交媒体**: Twitter/X (大咖动态), 微博 (国内热点)
    - **主流媒体**: TechCrunch, The Verge, 36氪, 虎嗅
    - **移动端**: 微信公众号热文
- **🉐 智能翻译**: 自动调用 Google Cloud Translation API 将英文标题与摘要翻译为中文，支持中英对照显示。
- **📩 自动订阅系统**:
    - 支持通过发送邮件 **“订阅AI资讯日报”** 自动加入名单。
    - 支持发送 **“退订AI资讯日报”** 自动移除名单。
    - **每小时**自动巡检收件箱，1 小时内发出正式确认函。
- **🛡️ 智能过滤与去重**:
    - 基于强大的 AI 关键词库（GPT-4o, Sora, RAG 等）过滤无关信息。
    - 采用文本相似度算法（Levenshtein）自动剔除重复资讯。
- **📊 权重排序**: 综合考量时间时效（24h内优先）、来源质量与社交热度，选取 Top 30。

## 🚀 快速开始 (GitHub Actions 部署)

### 1. 配置 GitHub Secrets
在仓库的 `Settings -> Secrets and variables -> Actions` 中添加：

| 名称 | 说明 | 必填 |
|------|------|------|
| `EMAIL_USER` | 您的 Gmail 地址 (建议使用专用账号) | ✅ |
| `EMAIL_PASSWORD` | Gmail **应用专用密码** (16位) | ✅ |
| `EMAIL_TO` | 管理员邮箱地址 | ✅ |
| `GOOGLE_TRANSLATE_API_KEY` | Google Cloud Translation API Key | ✅ |
| `GOOGLE_PROJECT_ID` | Google Cloud 项目 ID | ✅ |

### 2. 开启 Gmail IMAP 权限
1. 登录 Gmail，进入 **设置 -> 查看所有设置 -> 转发和 POP/IMAP**。
2. 勾选 **启用 IMAP** 并保存。

### 3. 设置即时反馈 (Gmail 过滤器)
为了让订阅者发信后立即收到回执，请在 Gmail 中设置：
1. **启用模板**：设置 -> 高级 -> 启用“模板”。
2. **存为模板**：写一封草稿回复用户，存为新模板（如“处理中”）。
3. **创建过滤器**：搜索 `订阅 OR 退订 OR 日报`，创建过滤器并选择 **“发送模板”**。

---

## 🛠️ 项目结构说明

- `src/main.py`: 主程序，控制日报生成全流程。
- `src/notifier/subscriber_manager.py`: 核心订阅逻辑，支持正则匹配与最后意愿优先。
- `src/processors/translator.py`: 翻译逻辑，支持 Google REST API 与 异常降级。
- `data/subscribers.txt`: 订阅名单，由机器人自动维护，请勿手动编辑（除非紧急干预）。
- `.github/workflows/`: 
    - `daily_news.yml`: 每天 08:23 运行日报发送。
    - `sub_sync_hourly.yml`: 每小时运行一次订阅同步。

---

## 📅 维护指南

- **如何修改发送数量？** 修改 `src/main.py` 中的 `top_n=30`。
- **如何增加大V关注？** 在 `src/config.py` 的 `TWITTER_USERS` 中添加用户名。
- **如何调整 AI 关键词？** 在 `src/config.py` 的 `AI_KEYWORDS` 中增删。
- **系统变慢了？** 检查 GitHub Actions 运行记录，确认是否有爬虫超时或 Nitter 实例失效。

## 📜 许可证

MIT License.
