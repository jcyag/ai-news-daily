# AI资讯日报

每天自动爬取全网AI相关资讯，精选Top 10发送到你的邮箱。

## 功能特点

- **多数据源**: 36氪、虎嗅、TechCrunch、The Verge、Hacker News、Reddit、搜狗搜索
- **智能过滤**: 基于AI关键词自动过滤相关内容
- **去重排序**: 相似内容去重，按时效性和热度排序
- **精美邮件**: 响应式HTML邮件模板，支持手机阅读
- **定时推送**: 通过GitHub Actions每天早上8点自动推送

## 数据源

| 来源 | 方法 | 说明 |
|------|------|------|
| 36氪 | RSS | 中文科技媒体 |
| 虎嗅 | RSS | 中文科技媒体 |
| TechCrunch | RSS | AI专栏 |
| The Verge | RSS | 科技新闻 |
| Hacker News | API | 技术社区热帖 |
| Reddit | OAuth API | r/MachineLearning |
| 搜狗搜索 | 网页爬取 | AI相关搜索结果 |

## 快速开始

### 1. Fork本仓库

点击右上角 Fork 按钮

### 2. 配置GitHub Secrets

在仓库设置 -> Secrets and variables -> Actions 中添加：

| Secret名称 | 说明 | 必填 |
|------------|------|------|
| `EMAIL_USER` | Gmail地址 | ✅ |
| `EMAIL_PASSWORD` | Gmail应用专用密码 | ✅ |
| `EMAIL_TO` | 收件人邮箱 | ✅ |
| `REDDIT_CLIENT_ID` | Reddit API ID | ❌ |
| `REDDIT_CLIENT_SECRET` | Reddit API Secret | ❌ |

### 3. 获取Gmail应用专用密码

1. 登录 [Google账户](https://myaccount.google.com/)
2. 进入 **安全性** -> **两步验证**（需要先开启）
3. 在两步验证页面底部，点击 **应用专用密码**
4. 选择应用类型为"邮件"，生成16位密码
5. 将此密码填入 `EMAIL_PASSWORD`

### 4. (可选) 获取Reddit API凭据

1. 登录 Reddit，访问 [Apps](https://www.reddit.com/prefs/apps)
2. 点击 "create another app..."
3. 选择 "script" 类型
4. 填写名称和描述，redirect uri 填 `http://localhost`
5. 创建后获取 client_id（应用名下方的字符串）和 secret

### 5. 启用GitHub Actions

1. 进入仓库的 Actions 页面
2. 点击 "I understand my workflows, go ahead and enable them"
3. 选择 "Daily AI News" workflow
4. 点击 "Run workflow" 手动测试一次

## 本地运行

```bash
# 克隆仓库
git clone https://github.com/your-username/ai-news-daily.git
cd ai-news-daily

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置

# 运行
cd src
python main.py
```

## 项目结构

```
ai-news-daily/
├── src/
│   ├── main.py              # 主程序入口
│   ├── config.py            # 配置管理
│   ├── crawlers/            # 爬虫模块
│   │   ├── base.py          # 基础类和数据模型
│   │   ├── rss_crawler.py   # RSS爬虫
│   │   ├── hackernews.py    # Hacker News API
│   │   ├── reddit.py        # Reddit API
│   │   └── sogou.py         # 搜狗搜索
│   ├── processors/          # 数据处理
│   │   ├── filter.py        # AI关键词过滤
│   │   ├── dedup.py         # 去重
│   │   └── ranker.py        # 排序
│   └── notifier/
│       └── email_sender.py  # 邮件发送
├── templates/
│   └── email_template.html  # 邮件模板
├── .github/workflows/
│   └── daily_news.yml       # GitHub Actions配置
├── requirements.txt
├── .env.example
└── README.md
```

## 自定义配置

### 修改推送时间

编辑 `.github/workflows/daily_news.yml`:

```yaml
on:
  schedule:
    # 北京时间早上8点 = UTC 0点
    - cron: '0 0 * * *'
```

Cron表达式格式: `分 时 日 月 星期`（UTC时间）

### 修改AI关键词

编辑 `src/config.py` 中的 `AI_KEYWORDS` 列表

### 修改选取数量

编辑 `src/main.py` 中的 `top_n` 参数：

```python
top_news = process_news(all_news, top_n=10)  # 改为你想要的数量
```

## 注意事项

1. **搜狗搜索**: 有较强的反爬机制，可能偶尔失败，不影响其他数据源
2. **Reddit**: 需要单独申请API凭据，不配置会自动跳过
3. **GitHub Actions**: 免费账户每月有2000分钟额度，本项目每次运行约2-3分钟
4. **邮件频率**: 默认每天一次，避免对数据源造成压力

## License

MIT
