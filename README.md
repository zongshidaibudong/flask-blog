# 代凯文的工程图板

基于 Flask 与 Markdown 的个人技术博客。文章以 `.md` 文件形式存放在 `posts/` 目录，无需数据库。

## 功能

- 首页文章列表（按日期倒序）
- 文章详情页
- 归档页
- 标签分类
- 关于页
- 404 页面
- 内置 CSP、X-Frame-Options 等安全响应头

## 运行

```bash
pip install -r requirements.txt
python app.py
```

浏览器访问 http://127.0.0.1:5000

## 写文章

在 `posts/` 下新建 `.md` 文件，头部元信息：

```
title: 文章标题
date: 2026-08-20
tags: Python, Flask
summary: 一句话摘要
```

正文使用 Markdown 语法。

## 目录结构

```
blog/
├── app.py              # Flask 应用入口
├── requirements.txt    # 依赖
├── posts/              # Markdown 文章
├── static/             # 静态资源（CSS、图片）
└── templates/          # Jinja2 模板
```
