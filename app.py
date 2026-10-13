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

import markdown
from flask import Flask, abort, render_template

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"

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


def load_posts():
    """读取 posts/ 目录下所有 Markdown 文章，按日期倒序返回。"""
    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        md = markdown.Markdown(
            extensions=["extra", "meta", "toc"],
            output_format="html5",
            # Markdown files are local content. Do not pass raw HTML through to
            # the template's `|safe` rendering, otherwise a post could become
            # stored XSS if an untrusted file is copied into posts/.
            html_replacement_text="",
        )
        html = md.convert(path.read_text(encoding="utf-8"))
        meta = md.Meta  # 形如 {key: [value]}
        posts.append(
            {
                "slug": path.stem,
                "title": meta.get("title", ["未命名"])[0],
                "date": meta.get("date", ["1970-01-01"])[0],
                "tags": [
                    t.strip()
                    for t in meta.get("tags", [""])[0].split(",")
                    if t.strip()
                ],
                "summary": meta.get("summary", [""])[0],
                "content": html,
            }
        )
    posts.sort(key=lambda p: p["date"], reverse=True)
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
    return render_template("tag.html", tag=tag, posts=posts)


@app.route("/about/")
def about():
    return render_template("about.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
