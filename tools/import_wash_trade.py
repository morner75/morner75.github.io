#!/usr/bin/env python3
"""워시 트레이딩 해설 페이지(단독 HTML)를 블로그 페이지로 가져온다.

원본의 본문만 꺼내 research/wash-trading/index.qmd를 만들고, 내장 그림은
figures/ 아래 PNG 파일로 분리한다. 스타일은 wash-trading.css에서 따로 관리한다.
원본 폴더는 수정하지 않으며, 원본이 바뀌면 다시 실행하면 된다.

실행: python3 tools/import_wash_trade.py [원본 index.html]
"""
import base64
import hashlib
import re
import sys
from pathlib import Path

DEFAULT_SOURCE = Path("/home/morner/writing/wash_trade/html/index.html")
OUT_DIR = Path(__file__).resolve().parents[1] / "research" / "wash-trading"
FIG_DIR = OUT_DIR / "figures"
PUBLISHED = "2026-11-04"
# 블로그와 CV에서는 원고를 Working paper로 표기한다.
RELABEL = {
    "금융감독연구 투고 원고(2026년 11월)": "Working paper(2026년 11월)",
    "(금융감독연구 투고본, 2026년 11월)": "(Working paper, 2026년 11월)",
}

SCRIPT = """<script>
(function(){
  var open=document.getElementById('openall');
  if(open) open.addEventListener('click',function(){
    var d=document.querySelectorAll('.wt #appendix details'), any=[].some.call(d,function(x){return !x.open});
    [].forEach.call(d,function(x){x.open=any}); open.textContent=any?'모두 접기':'모두 펼치기';
  });
  var links=[].slice.call(document.querySelectorAll('.wt-toc a')), secs=links.map(function(a){return document.querySelector(a.getAttribute('href'))});
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){var i=secs.indexOf(e.target);links.forEach(function(l,j){l.classList.toggle('on',i===j)})}})},{rootMargin:'-20% 0px -70% 0px'});
    secs.forEach(function(s){s&&io.observe(s)});
  }
})();
</script>"""


def take(pattern, text, label):
    match = re.search(pattern, text, re.S)
    if not match:
        sys.exit(f"원본에서 찾지 못함: {label}")
    return match


def extract_images(body):
    """내장 PNG를 파일로 저장하고 상대 경로로 바꾼다. 같은 그림은 한 번만 저장한다."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for old in FIG_DIR.glob("fig-*.png"):
        old.unlink()
    names = {}

    def replace(match):
        data = base64.b64decode(match.group(1))
        key = hashlib.sha256(data).hexdigest()
        if key not in names:
            names[key] = f"fig-{len(names) + 1:02d}.png"
            (FIG_DIR / names[key]).write_bytes(data)
        return f"figures/{names[key]}"

    return re.sub(r"data:image/png;base64,([A-Za-z0-9+/=]+)", replace, body), len(names)


def yaml_str(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    html = source.read_text(encoding="utf-8")
    for old, new in RELABEL.items():
        if old not in html:
            sys.exit(f"원본에서 찾지 못함: {old}")
        html = html.replace(old, new)

    description = take(r'<meta name="description" content="([^"]+)"', html, "description").group(1)
    body = take(r"<main>(.*)</main>", html, "main").group(1)
    toc = take(r'<nav class="toc"[^>]*>(.*?)</nav>', html, "목차").group(1)
    title = take(r"<h1>(.*?)</h1>", body, "제목").group(1)
    kicker = take(r'<div class="kicker">(.*?)</div>', body, "머리말").group(1)

    # 제목과 머리말은 블로그의 제목 영역으로 옮기고, 꼬리말은 전역 스타일과 겹치지 않게 바꾼다.
    body = re.sub(r"\s*<h1>.*?</h1>", "", body, count=1, flags=re.S)
    body = re.sub(r'\s*<div class="kicker">.*?</div>', "", body, count=1, flags=re.S)
    body = re.sub(r'<header class="hero" id="summary">', '<div class="hero" id="summary">', body, count=1)
    body = body.replace("</header>", "</div>", 1)
    body = body.replace("<footer>", '<div class="wt-foot">', 1).replace("</footer>", "</div>", 1)

    body, n_images = extract_images(body)
    if "```" in body or "data:image" in body:
        sys.exit("본문에 처리할 수 없는 내용이 남아 있습니다.")

    page = f"""---
# tools/import_wash_trade.py가 생성한 파일입니다. 내용은 원본에서 고친 뒤 다시 실행하세요.
title: {yaml_str(title)}
subtitle: {yaml_str(kicker)}
description: {yaml_str(description)}
date: {PUBLISHED}
date-format: "YYYY년 M월"
categories: ["가상자산", "워시 트레이딩", "벤포드 법칙"]
image: figures/fig-01.png
lang: ko
page-layout: full
toc: false
css:
  - ../research.css
  - wash-trading.css
resources:
  - figures/*.png
---

```{{=html}}
<div class="wt"><div class="wt-grid">
<div class="wt-main">
{body}
</div>
<nav class="wt-toc" aria-label="목차">{toc}</nav>
</div></div>
{SCRIPT}
```
"""
    (OUT_DIR / "index.qmd").write_text(page, encoding="utf-8")
    size = sum(p.stat().st_size for p in FIG_DIR.glob("*.png")) / 1e6
    print(f"{OUT_DIR / 'index.qmd'}: 그림 {n_images}개 ({size:.1f} MB)")


if __name__ == "__main__":
    main()
