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
from html.parser import HTMLParser

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"

# 最近一次 load_posts() 跳过的文件（文件名, 原因）。导出脚本据此判断是否要失败退出。
SKIPPED_POSTS = []

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


# python-markdown 3.x 已移除 safe_mode，html_replacement_text 这类旧参数会被静默忽略，
# 原文 HTML 会直通到模板的 |safe。下面用一棵"白名单重建"的思路清洗：
# 用 HTMLParser 把片段拆成 token，只保留允许的标签与属性再重新拼回去。
# 之所以不用正则删黑名单：删掉一段后两侧会重新拼接，<scr<script>ipt> 能拼出真的
# <script>；正则还会把正文里"onclick=alert(1)"这种讲解文字一起吃掉。
class _Sanitizer(HTMLParser):
    """只保留白名单标签与属性，重建一份干净的 HTML。"""

    ALLOWED_TAGS = {
        "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li", "blockquote", "pre", "code", "kbd", "samp",
        "em", "strong", "b", "i", "u", "s", "del", "ins", "mark", "small",
        "sub", "sup", "span", "div", "figure", "figcaption", "caption",
        "table", "thead", "tbody", "tfoot", "tr", "th", "td",
        "a", "img", "dl", "dt", "dd", "abbr", "time",
    }
    VOID_TAGS = {"br", "hr", "img"}
    # 这些标签连同内部文字一起丢弃
    DROP_CONTENT = {
        "script", "style", "iframe", "object", "embed", "form", "input",
        "textarea", "select", "button", "link", "meta", "base", "noscript",
        "template", "svg", "math",
    }
    ALLOWED_ATTRS = {
        "*": {"class", "id", "title", "lang", "dir"},
        "a": {"href", "hreflang"},
        "img": {"src", "alt", "width", "height", "loading"},
        "th": {"colspan", "rowspan", "scope"},
        "td": {"colspan", "rowspan"},
        "ol": {"start", "reversed"},
        "time": {"datetime"},
        "abbr": set(),
    }
    URL_ATTRS = {"href", "src", "xlink:href", "action", "formaction", "poster"}
    UNSAFE_SCHEMES = ("javascript:", "vbscript:", "data:text/html")

    def __init__(self):
        super().__init__(convert_charrefs=True)  # 属性值里的实体自动解码
        self._out = []
        self._drop_depth = 0

    # --- 工具 ---
    @staticmethod
    def _safe_url(value: str) -> str:
        cleaned = "".join(ch for ch in value if ord(ch) > 0x20).strip()
        if cleaned.lower().startswith(_Sanitizer.UNSAFE_SCHEMES) or "javascript:" in cleaned.lower():
            return "#"
        return value

    def _render_attrs(self, tag, attrs):
        allowed = self.ALLOWED_ATTRS.get(tag, set()) | self.ALLOWED_ATTRS["*"]
        pieces = []
        for name, value in attrs:
            name = (name or "").lower()
            if not name or name.startswith("on"):
                continue  # 内联事件一律不保留
            if name not in allowed:
                continue
            value = "" if value is None else value
            if name in self.URL_ATTRS:
                value = self._safe_url(value)
            pieces.append(f' {name}="{html_lib.escape(value, quote=True)}"')
        return "".join(pieces)

    # --- HTMLParser 回调 ---
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.DROP_CONTENT:
            self._drop_depth += 1
            return
        if self._drop_depth or tag not in self.ALLOWED_TAGS:
            return
        self._out.append(f"<{tag}{self._render_attrs(tag, attrs)}>")

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.DROP_CONTENT or self._drop_depth or tag not in self.ALLOWED_TAGS:
            return
        self._out.append(f"<{tag}{self._render_attrs(tag, attrs)}>")
        if tag not in self.VOID_TAGS:
            self._out.append(f"</{tag}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.DROP_CONTENT:
            if self._drop_depth:
                self._drop_depth -= 1
            return
        if self._drop_depth or tag not in self.ALLOWED_TAGS or tag in self.VOID_TAGS:
            return
        self._out.append(f"</{tag}>")

    def handle_data(self, data):
        if self._drop_depth:
            return
        self._out.append(html_lib.escape(data, quote=False))

    def result(self) -> str:
        return "".join(self._out)


def sanitize_html(html):
    """按白名单重建 HTML 片段，丢弃脚本、事件属性与危险协议的链接。"""
    parser = _Sanitizer()
    parser.feed(html)
    parser.close()
    return parser.result()


def parse_date(value):
    """把 date 元信息解析成日期，解析失败时退回到最早，避免排序错位。"""
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.min


def load_posts():
    """读取 posts/ 目录下所有 Markdown 文章，按日期倒序返回。

    单篇文章读不了或解析失败时跳过该篇，不拖垮整站；但代价要让人看得见：
    跳过会写一条 app.logger 警告，同时记进 SKIPPED_POSTS，导出脚本据此失败退出。
    """
    global SKIPPED_POSTS
    posts = []
    skipped = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:  # 编码错、文件被占用等
            skipped.append((path.name, f"读取失败：{exc}"))
            continue

        try:
            md = markdown.Markdown(extensions=["extra", "meta", "toc"], output_format="html5")
            html = md.convert(text)
            meta = md.Meta  # 形如 {key: [value]}
        except Exception as exc:  # noqa: BLE001 —— 坏文件不该让整站 500
            skipped.append((path.name, f"解析失败：{exc}"))
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
    for name, reason in skipped:
        app.logger.warning("跳过文章 %s（%s）—— 该篇详情页与其标签页会不可用", name, reason)
    SKIPPED_POSTS = skipped
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
