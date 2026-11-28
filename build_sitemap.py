# -*- coding: utf-8 -*-
"""sitemap.xml 만들기 — site/ 아래 개체 화면 + 공개 화면 목록.

왜 필요한가: 목록 화면들이 JSON 을 받아 자바스크립트로 그리기 때문에, 자바스크립트를
돌리지 않는 크롤러에게는 /list 의 정적 링크 1,000개 남짓만 보인다. 개체 화면 8,700여 개가
고아 쪽으로 남으므로 사이트맵으로 직접 알린다.

규칙
  · 주소는 .html 없는 깔끔한 쪽을 쓴다(사이트가 .html 을 307 로 넘긴다).
  · <meta name="robots" content="noindex"> 가 붙은 넘김쪽(리디렉션 껍데기)은 뺀다.
  · <lastmod> 는 파일이 바뀐 날(한국 날짜가 아니라 파일 시각의 날짜)로 적는다.
  · 공개 화면은 아래 PAGES 에 적은 것만 — 404·관리자 검토(admin)·틀 화면(entity)은 뺀다.

쓰는 법: py build_sitemap.py   (deploy.ps1 이 배포 전에 부른다)
사이트맵이 배포되려면 .assetsignore 에 `!/sitemap.xml` 예외가 있어야 한다 — *.xml 이 막혀 있다.
"""

import io
import os
import re
from datetime import datetime, timezone

SITE = "https://kcritic.kr"
HERE = os.path.dirname(os.path.abspath(__file__))
DIRS = ("essays", "critics", "writers", "thinkers")

# 공개 화면. index 는 "/" 로 들어간다. 여기에 없는 최상위 .html 은 사이트맵에 안 들어간다
# (404 = 오류 화면, admin = 관리자 검토, entity = 질의 문자열이 있어야 뜻이 생기는 틀 화면).
PAGES = [
    "index", "about", "academic-network", "ask", "concepts", "contribute",
    "criticism", "critics", "data", "evaluate", "evaluate-essay", "explore",
    "graph", "lineage", "list", "maker", "research", "school", "search",
    "sparql", "study", "thinkers", "writers",
]

NOINDEX = re.compile(r"""name\s*=\s*["']robots["'][^>]*noindex""", re.I)


def lastmod(path):
    return datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).strftime("%Y-%m-%d")


def indexable(path):
    """넘김쪽(noindex 껍데기)이면 False."""
    with io.open(path, encoding="utf-8", errors="replace") as f:
        return not NOINDEX.search(f.read(1200))


def entries():
    out, skipped = [], 0
    for name in PAGES:
        p = os.path.join(HERE, name + ".html")
        if not os.path.exists(p):
            print("  [건너뜀] %s.html 이 없습니다" % name)
            continue
        loc = SITE + "/" if name == "index" else "%s/%s" % (SITE, name)
        out.append((loc, lastmod(p), "0.8" if name == "index" else "0.6"))

    for d in DIRS:
        folder = os.path.join(HERE, "site", d)
        if not os.path.isdir(folder):
            print("  [건너뜀] site/%s 폴더가 없습니다" % d)
            continue
        n = 0
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith(".html"):
                continue
            p = os.path.join(folder, fn)
            if not indexable(p):
                skipped += 1
                continue
            out.append(("%s/site/%s/%s" % (SITE, d, fn[:-5]), lastmod(p), "0.5"))
            n += 1
        print("  site/%-9s %5d 쪽" % (d, n))
    return out, skipped


def main():
    rows, skipped = entries()
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, mod, pri in rows:
        body.append("  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>"
                    % (loc.replace("&", "&amp;"), mod, pri))
    body.append("</urlset>")
    body.append("")
    text = "\n".join(body)

    if len(rows) > 50000:
        raise SystemExit("주소가 %d 개입니다 — 한 파일 한도 50,000 을 넘었습니다. 쪼개야 합니다." % len(rows))

    out = os.path.join(HERE, "sitemap.xml")
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print("  넘김쪽(noindex) %d 쪽은 뺐습니다" % skipped)
    print("  sitemap.xml — 주소 %d 개, %.1f KB" % (len(rows), len(text.encode("utf-8")) / 1024.0))


if __name__ == "__main__":
    main()
