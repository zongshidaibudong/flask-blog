"""个人技术博客 - Flask 应用入口。

文章以 Markdown 文件形式存放在 posts/ 目录中，
文件头部使用 `key: value` 元信息（由 markdown 的 meta 扩展解析）：

    title: 文章标题
    date: 2026-08-20
    tags: Python, Flask
    summary: 一句话摘要

运行方式：
    python app.py
    然后浏览器访问 http://127.0.0.1:5000
"""
from datetime import datetime
from pathlib import Path
import html as html_lib
import os
import re

import markdown
from flask import Flask, abort, render_template

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"

# 站点对外地址：分享卡片（Open Graph）要求 og:image / og:url 是绝对地址。
# 部署到自己的域名时，改这里或用环境变量 SITE_URL 覆盖。
SITE_URL = (
    os.environ.get("SITE_URL")
    or "https://welcome-crocodile-d75ecc93ae662-1516600636.tcloudbaseapp.com"
).rstrip("/")

app = Flask(__name__)


@app.after_request
def add_security_headers(response):
    """Add browser-side defenses appropriate for this read-only blog."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self'; img-src 'self' data:; "
        "script-src 'none'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
    )
    return response


# Markdown 里可能出现的危险片段。python-markdown 3.x 已移除 safe_mode，
# 传 html_replacement_text 这类旧参数会被静默忽略，所以原文 HTML 会直通；
# 这里在渲染后按白名单做一次清洗，配合模板里的 CSP 作为第二道防线。
_DANGEROUS_TAGS = re.compile(
    r"<\s*(script|style|iframe|object|embed|form|link|meta)\b[^>]*>.*?<\s*/\s*\1\s*>"
    r"|<\s*(script|style|iframe|object|embed|form|link|meta)\b[^>]*/?>",
    re.IGNORECASE | re.DOTALL,
)
_EVENT_ATTR = re.compile(r"""\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)
# 无引号写法：href=javascript:...
_BAD_URL = re.compile(r"""(href|src)\s*=\s*(javascript:|data:text/html|vbscript:)""", re.IGNORECASE)
_ATTR_WITH_URL = re.compile(r"""\b(href|src)(\s*=\s*)(["'])(.*?)\3""", re.IGNORECASE | re.DOTALL)
_UNSAFE_SCHEMES = ("javascript:", "data:text/html", "vbscript:")


def _clean_url_attrs(html_text: str) -> str:
    """逐个检查 href/src 的值，先做实体解码再判协议，防止 java&#115;cript: 绕过。"""

    def repl(match: re.Match) -> str:
        attr, eq, quote, value = match.group(1), match.group(2), match.group(3), match.group(4)
        decoded = html_lib.unescape(value).strip().lower().replace("\t", "").replace("\n", "")
        if decoded.startswith(_UNSAFE_SCHEMES) or "javascript:" in decoded:
            return f"{attr}{eq}{quote}#{quote}"
        return match.group(0)

    return _ATTR_WITH_URL.sub(repl, html_text)


def sanitize_html(html):
    """去掉脚本、内联事件与危险协议的链接，保留正常的排版标签。"""
    cleaned = _DANGEROUS_TAGS.sub("", html)
    cleaned = _EVENT_ATTR.sub("", cleaned)
    cleaned = _BAD_URL.sub(r"\1=\2#", cleaned)
    cleaned = _clean_url_attrs(cleaned)
    return cleaned


def parse_date(value):
    """把 date 元信息解析成日期，解析失败时退回到最早，避免排序错位。"""
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.min


def load_posts():
    """读取 posts/ 目录下所有 Markdown 文章，按日期倒序返回。

    单篇文章解析失败只跳过该篇并打印一条警告，不拖垮整站。
    """
    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:  # 编码错、文件被占用等
            print(f"[warn] 跳过无法读取的文章 {path.name}: {exc}")
            continue

        try:
            md = markdown.Markdown(extensions=["extra", "meta", "toc"], output_format="html5")
            html = md.convert(text)
            meta = md.Meta  # 形如 {key: [value]}
        except Exception as exc:  # noqa: BLE001 —— 坏文件不该让整站 500
            print(f"[warn] 跳过解析失败的文章 {path.name}: {exc}")
            continue

        raw_date = meta.get("date", ["1970-01-01"])[0]
        posts.append(
            {
                "slug": path.stem,
                "title": meta.get("title", ["未命名"])[0],
                "date": raw_date,
                "date_obj": parse_date(raw_date),
                # 中英文逗号都当分隔符，避免 "Python，Flask" 被当成一个标签
                "tags": [
                    t.strip()
                    for t in re.split(r"[,，]", meta.get("tags", [""])[0])
                    if t.strip()
                ],
                "summary": meta.get("summary", [""])[0],
                "content": sanitize_html(html),
            }
        )
    posts.sort(key=lambda p: (p["date_obj"], p["slug"]), reverse=True)
    return posts


def get_post(slug):
    for post in load_posts():
        if post["slug"] == slug:
            return post
    return None


@app.context_processor
def inject_globals():
    posts = load_posts()
    tags = sorted({t for p in posts for t in p["tags"]})
    return {
        "site_name": "代凯文的工程图板",
        "site_url": SITE_URL,
        "site_description": "机械工程在读，记录建模、制图与编程的日常。",
        "all_tags": tags,
        "current_year": datetime.now().year,
    }


@app.route("/")
def index():
    return render_template("index.html", posts=load_posts())


@app.route("/post/<slug>/")
def post_detail(slug):
    post = get_post(slug)
    if post is None:
        abort(404)
    return render_template("post.html", post=post)


@app.route("/archive/")
def archive():
    return render_template("archive.html", posts=load_posts())


@app.route("/tag/<tag>/")
def tag_posts(tag):
    posts = [p for p in load_posts() if tag in p["tags"]]
    if not posts:
        # 不存在的标签直接 404，避免返回一个空白的 200 页面
        abort(404)
    return render_template("tag.html", tag=tag, posts=posts)


@app.route("/about/")
def about():
    return render_template("about.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
