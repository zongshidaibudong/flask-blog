# 代凯文的工程图板

## 一、这是什么

> 一个不用数据库的个人技术博客：每篇文章就是一个 Markdown 文件，Flask 在请求时把它读出来渲染成页面；同一套代码还能用仓库里的脚本导出成静态站，直接扔到静态托管上。

![首页截图](docs/home.png)

## 二、在线地址

<https://welcome-crocodile-d75ecc93ae662-1516600636.tcloudbaseapp.com/>

线上跑的是用 `tools/export_static.py` 导出的静态版（`dist/`），托管在腾讯云开发 CloudBase 静态网站托管，使用默认域名，未绑定自有域名。

> 注意区分两种运行形态：**Flask 本地服务**有完整的 HTTP 安全响应头（含 `frame-ancestors`，可防点击劫持）；**线上静态站**拿不到响应头，只能靠页面里的 `<meta http-equiv="Content-Security-Policy">`。meta 不认 `frame-ancestors`，所以静态站没有点击劫持防护，其余（脚本、样式、图片、object、base-uri）与本地一致。

## 三、功能列表

- **首页文章列表** —— 按日期倒序排列，顶部是从全部文章自动汇总去重生成的标签云
- **文章详情** —— Markdown 渲染成 HTML，页面上展示标题、日期与标签（摘要只用于列表页和分享卡片，详情页不重复显示）；文章不存在时返回 404
- **归档页** —— 把全部文章按时间倒序列成时间线
- **标签筛选** —— `/tag/<tag>/` 只看某个标签下的文章；标签不存在时返回 404 而不是空白页
- **关于页** —— 静态介绍页
- **自定义 404** —— 未知路径返回友好错误页，不暴露堆栈
- **零数据库写作** —— 往 `posts/` 丢一个带元信息的 `.md` 就完成发文，不改代码、不重启服务
- **内容清洗** —— Markdown 渲染后用 HTML 解析器按白名单**重建**：只保留排版类标签，`<script>`/`<iframe>`/`<svg>`/`<style>` 连同内容一起丢弃，`on*` 事件属性一律不保留，`href`/`src` 先解码再判协议
- **安全响应头** —— Flask 侧每条响应都带 `Content-Security-Policy`、`X-Frame-Options`、`X-Content-Type-Options`、`Referrer-Policy`
- **图标与分享卡片** —— 自绘 favicon（SVG + PNG + iOS 图标），全站带 Open Graph / Twitter Card，分享出去有封面图
- **静态导出** —— `tools/export_static.py` 一条命令把 17 个页面导出到 `dist/`，并自动检查页面内的本地引用是否齐全

## 四、技术栈与目录结构

| 层 | 选型 |
|---|---|
| 语言 / 运行时 | Python 3.10+（本项目在 3.12 下开发；markdown 3.10.3 要求 ≥3.10） |
| Web 框架 | Flask 3.1.3 |
| 模板引擎 | Jinja2（模板继承，公共骨架在 `base.html`） |
| Markdown | markdown 3.10.3，启用 `extra` / `meta` / `toc` 扩展 |
| 数据库 | 无 |

路由一览（`app.py` 注册 6 条路由 + 1 个 404 处理器；路由只声明 GET，HEAD 由 Flask 自动支持）：

| 路由 | 说明 |
|---|---|
| `/` | 首页：文章列表 + 标签云 |
| `/post/<slug>/` | 文章详情，`slug` 即 `.md` 的文件名；不存在返回 404 |
| `/archive/` | 归档页 |
| `/tag/<tag>/` | 按标签筛选；无匹配返回 404 |
| `/about/` | 关于页 |
| `/static/<path>` | 静态资源（Flask 内置） |

```
blog/
├── app.py                 # 入口：路由、文章解析与清洗、安全响应头、404
├── requirements.txt       # 依赖清单（已锁定精确版本）
├── README.md              # 本文件
├── .gitignore
├── tools/
│   └── export_static.py   # 静态导出脚本：生成 dist/ 并校验本地引用
├── posts/                 # 4 篇 Markdown 文章 —— 内容源在这里
│   ├── engineering-drawing-basics.md
│   ├── gb-standard-parts.md
│   ├── nx-python-automation.md
│   └── vise-assembly-notes.md
├── templates/             # 7 个 Jinja2 模板
│   ├── base.html          # 公共骨架：CSP meta、分享卡片、图标、导航、页脚
│   ├── index.html         # 首页：文章卡片 + 标签云
│   ├── post.html          # 文章详情
│   ├── archive.html       # 归档
│   ├── tag.html           # 标签筛选
│   ├── about.html         # 关于
│   └── 404.html           # 错误页
├── static/
│   ├── css/style.css      # 工程图纸蓝图风样式（含移动端媒体查询）
│   └── assets/            # banner / logo / favicon / og-cover
├── docs/                  # README 用的截图
└── dist/                  # 静态导出产物（线上托管的就是这一份）
```

## 五、本地运行方法

```bash
# 1. 安装依赖（需要 Python 3.10+）
pip install -r requirements.txt

# 2. 启动
python app.py
```

浏览器打开 <http://127.0.0.1:5000>，`Ctrl + C` 停止。

**新增一篇文章**：在 `posts/` 下新建 `.md`，头部写元信息，正文写 Markdown，刷新页面即可，无需重启。

```
title: 文章标题
date: 2026-08-20
tags: Python, Flask
summary: 一句话摘要
```

> `date` 请用 `YYYY-MM-DD`；解析失败的文章会被排到列表末尾。`tags` 中英文逗号都支持。

**改完内容要同步静态版**：

```bash
python tools/export_static.py          # 重新生成 dist/，并自检本地引用
```

脚本会导出首页、全部文章、归档、关于、各个标签页与 404（当前 4 篇文章 + 9 个标签，共 17 个页面），最后打印缺失引用数（正常应为 0）。文章增删后页数会跟着变；如果有文章读不出来被跳过，脚本会直接中止并返回非零，不会静默少导。

**只想本地看静态版**：

```bash
cd dist
python -m http.server 8000
# 打开 http://127.0.0.1:8000
```

> `dist/` 里的资源引用是 `/static/...` 这种以站点根目录为准的绝对路径，所以不要直接双击 HTML 文件，要放到网站根目录，或者像上面这样起个本地静态服务器。

## 六、已知问题与后续计划

**已知问题**

1. **每个请求都会重复解析全部文章**：`load_posts()` 在模板注入器和视图里各调一次，一次请求会把 4 个 `.md` 读两遍、解析两遍，并且每次解析都新建一个 Markdown 实例。文章只有 4 篇时感知不到，上百篇会明显变慢。
2. **用的是 Flask 开发服务器**：`app.run(debug=False, host="127.0.0.1", port=5000)`，只适合本机调试；要跑动态服务得上 waitress / gunicorn。
3. **没有搜索、分页和 RSS**：文章多了列表页会一屏到底。
4. **`dist/` 要手动重新导出**：改 `posts/` 的文章、`templates/` 的模板、`static/` 的资源、`app.py` 的代码，都不会自动同步到线上，必须再跑一次 `tools/export_static.py` 并重新部署。
5. **静态站只能部署在站点根目录**：页面里是 `/static/...` 绝对路径，挂到子路径下会掉样式。
6. **标签名不能含 `/`**：`/tag/<tag>/` 用的是默认字符串转换器，标签写成 `CI/CD` 会生成走不通的链接。
7. **传参依赖只锁了顶层**：`flask`、`markdown` 已锁精确版本，但 Werkzeug、Jinja2 等传递依赖没有 lock 文件。
8. **文章读不出来会被跳过**：该篇详情页和它带出来的标签页都会变成 404，列表里的篇数也会少一篇。现在会写 `app.logger` 警告、导出脚本遇跳过即失败退出，但运行中的站点不会给访客任何提示。

**已修复**

- [x] `requirements.txt` 由 `>=` 改为精确版本（`flask==3.1.3` / `markdown==3.10.3`）
- [x] 原先用 `html_replacement_text=""` 试图禁止原始 HTML —— 该参数在 markdown 3.x 里已失效，改为渲染后按白名单重建（HTMLParser 解析后重建，不是正则删黑名单），并给静态站补上 CSP meta
- [x] 单篇文章编码错误或解析失败会导致整站 500 —— 改为跳过该篇 + `app.logger.warning`，导出脚本发现有文章被跳过就中止（返回码 2），不允许静默少页
- [x] `date` 按字符串排序、`tags` 只按半角逗号切分 —— 改为日期解析排序、中英文逗号都切
- [x] 访问不存在的标签返回 200 空白页 —— 改为 404
- [x] 没有 favicon 和分享卡片 —— 已补自绘图标与 Open Graph 元信息

**后续计划**

- [ ] 给 `load_posts()` 加一层缓存（按文件 mtime 失效），或在请求内用 `flask.g` 复用结果
- [ ] 加 RSS 与站内搜索
- [ ] 标签改用 slug（避免含 `/` 的标签生成死链）
- [ ] 部署改走 waitress + 反向代理
- [ ] 补一份 smoke test / CI，把 `export_static.py` 的自检挂到提交前
