#!/usr/bin/env python3
"""
안정 링크용 리다이렉트 페이지 생성 (GitHub Pages 배포용)

Doxygen 이 만든 사이트(docs_build/html)를 루트로 유지하면서, 그 아래에
심볼/요구사항 단위 리다이렉트 페이지를 엠는다.

  docs_build/html/sym/src/Aeb_FusionEngine.c/CalculateTTC/index.html
      -> https://github.com/{repo}/blob/{branch}/src/Aeb_FusionEngine.c#L36-L55

  docs_build/html/req/SRS-AEB-305/index.html
      -> 해당 요구사항의 구현/검증 위치를 모아 보여주는 랜딩 페이지

왜 리다이렉트인가:
  Codebeamer 요구사항 항목에 GitHub blob 링크(#L36-L55)를 직접 저장하면
  주석 한 줄 추가에도 링크가 어긋난다. 심볼 이름 기반 URL 을 ALM 에 저장하고,
  라인 번호는 CI 가 매번 다시 계산해 리다이렉트만 갱슱하면 링크가 언제나 유효하다.

입력: redirects_generated.json, req_index.json  (build_symbol_map.py 산출물)
"""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOXY_HTML = ROOT / "docs_build" / "html"
SYM_JSON = ROOT / "redirects_generated.json"
REQ_JSON = ROOT / "req_index.json"

REPO = os.environ.get("SYMLINK_REPO", "cnbissolution/cb_ai")
BRANCH = os.environ.get("SYMLINK_BRANCH", "main")

REDIRECT_TMPL = """<!doctype html>
<meta charset="utf-8">
<title>Redirecting to {label}</title>
<meta http-equiv="refresh" content="0; url={url}">
<link rel="canonical" href="{url}">
<script>window.location.replace({url_js});</script>
<p>자동 이동하지 않으니 <a href="{url}">여기를 클릭</a>하십시오.</p>
"""

KIND_LABEL = {"req": "구현", "verifies": "검증", "satisfies": "충족"}

REQ_PAGE_TMPL = """<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<title>{rid} — 추적 링크</title>
<style>
  body {{ font-family: system-ui, -apple-system, "Malgun Gothic", sans-serif;
         max-width: 900px; margin: 3rem auto; padding: 0 1rem; line-height: 1.6; }}
  h1 {{ font-size: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #d0d7de; padding: .5rem .75rem; text-align: left; }}
  th {{ background: #f6f8fa; }}
  code {{ background: #f6f8fa; padding: .1rem .35rem; border-radius: 4px; }}
  .kind {{ font-weight: 600; }}
  footer {{ margin-top: 2rem; color: #57606a; font-size: .9rem; }}
</style>
<h1>{rid}</h1>
<p>이 요구사항에 연결된 코드 위치입니다. 라인 번호는 최신 밑드 기준으로 자동 갱슱됩니다.</p>
<table>
  <tr><th>관계</th><th>심볼</th><th>파일</th><th>라인</th><th>이동</th></tr>
  {rows}
</table>
<footer>
  장재소 <code>{repo}</code> · 변경집 <code>{branch}</code><br>
  이 페이지는 <code>scripts/generate_redirects.py</code> 가 생성했습니다.
  ALM 항목에는 이 페이지 URL 을 저장하십시오 — 코드가 이동해도 링크가 유지됩니다.
</footer>
</html>
"""


def write_redirect(path: Path, url: str, label: str):
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text(
        REDIRECT_TMPL.format(url=html.escape(url, quote=True),
                             url_js=json.dumps(url),
                             label=html.escape(label)),
        encoding="utf-8",
    )


def main():
    if not SYM_JSON.exists():
        sys.exit("%s 가 없습니다. 먼젌 scripts/build_symbol_map.py 를 실행하십시오." % SYM_JSON.name)

    # Doxygen 산출물이 없어도 리다이렉트만 단독 생성할 수 있게 한다
    # (Pages 워크플로에서는 doxygen 이 먼저 돌아 docs_build/html 이 존재한다)
    out_root = DOXY_HTML if DOXY_HTML.exists() else (ROOT / "docs_build" / "html")
    if not DOXY_HTML.exists():
        print("[info] Doxygen 산출물이 없어 %s 를 새로 만들다 (리다이렉트 전용)" % out_root)
        out_root.mkdir(parents=True, exist_ok=True)

    sym = json.loads(SYM_JSON.read_text(encoding="utf-8"))
    if not sym:
        sys.exit("redirects_generated.json 이 비어 있습니다. 심볼을 찾지 못했습니다.")

    # ---- 심볼 리다이렉트 ----
    sym_dir = out_root / "sym"
    for key, url in sorted(sym.items()):
        target = sym_dir
        for part in key.split("/"):
            target = target / part
        write_redirect(target, url, key)
    print("[ok] 심볼 리다이렉트 %d개 -> %s" % (len(sym), sym_dir.relative_to(ROOT)))

    # ---- 요구사항 랜딩 페이지 ----
    req_count = 0
    if REQ_JSON.exists():
        req = json.loads(REQ_JSON.read_text(encoding="utf-8"))
        req_dir = out_root / "req"
        for rid, entries in sorted(req.items()):
            rows = []
            for e in entries:
                rows.append(
                    "<tr><td class='kind'>{kind}</td><td><code>{sym}</code></td>"
                    "<td><code>{file}</code></td><td>L{s}–L{e}</td>"
                    "<td><a href='{url}'>코드 보기</a></td></tr>".format(
                        kind=KIND_LABEL.get(e["kind"], e["kind"]),
                        sym=html.escape(e["symbol"]),
                        file=html.escape(e["file"]),
                        s=e["start"], e=e["end"],
                        url=html.escape(e["url"], quote=True),
                    )
                )
            page = req_dir / rid
            page.mkdir(parents=True, exist_ok=True)
            (page / "index.html").write_text(
                REQ_PAGE_TMPL.format(rid=html.escape(rid), rows="\n  ".join(rows),
                                     repo=html.escape(REPO), branch=html.escape(BRANCH)),
                encoding="utf-8",
            )
            req_count += 1
        print("[ok] 요구사항 페이지 %d개 -> %s" % (req_count, req_dir.relative_to(ROOT)))
    else:
        print("[info] req_index.json 없음 - 요구사항 페이지 생략")

    print("\n[done] 안정 링크 형식:")
    print("  https://%s.github.io/%s/sym/<경로>/<심볼>/" % tuple(REPO.split("/")))
    print("  https://%s.github.io/%s/req/<요구사항ID>/" % tuple(REPO.split("/")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
