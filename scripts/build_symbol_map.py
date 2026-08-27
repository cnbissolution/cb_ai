#!/usr/bin/env python3
"""
소스 코드 심볼 인덱스 생성 — SDD/요구사항에서 코드로 걸 '안 끊어지는 링크' 만들기

문제:
  추적성 문서에 `Aeb_FusionEngine.c:35` 처럼 라인 번호를 박아두면,
  주석 한 줄만 추가해도 전부 틀린 링크가 된다.
  (실제로 이 프로젝트에서 @req 주석을 넣자 35 -> 50 으로 밀렸다)

해법:
  심볼 이름 기준의 안정적인 URL 을 만든다.
    docs/sym/src/Aeb_FusionEngine.c/CalculateTTC/  ->  GitHub blob #L49-L60
  라인 번호가 바뀌면 인덱스만 다시 생성되고, ALM 에 저장한 링크는 그대로 유효하다.

  추가로 소스의 @req 주석을 파싱해 요구사항 단위 URL 도 만든다.
    docs/req/SRS-AEB-305/  ->  해당 요구사항을 구현한 코드 위치

출력:
  redirects_generated.json   심볼 -> GitHub blob 링크
  req_index.json             요구사항 ID -> 구현/검증 심볼 목록
  unit_index.json            유닛 ID(@unit) -> 심볼 + 상위 설계 ID
  docs/generated/CODE_INDEX.md   사람이 읽는 인덱스 표

환경변수:
  SYMLINK_REPO     기본 cnbissolution/cb_ai
  SYMLINK_BRANCH   기본 main

ctags(universal-ctags)가 있으면 사용하고, 없으면 정규식으로 대체한다.
CI 에는 ctags 를 설치하지만 로컬에서도 그냥 돌아가야 하기 때문이다.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = os.environ.get("SYMLINK_REPO", "cnbissolution/cb_ai")
BRANCH = os.environ.get("SYMLINK_BRANCH", "main")

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIRS = ["src", "test"]
C_SUFFIXES = {".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"}
PY_SUFFIXES = {".py"}
EXCLUDE_DIRS = {".git", ".github", "docs_build", "build", "__pycache__", "_archive"}

# @req SRS-AEB-305 / @verifies SRS-AEB-401 형태의 추적 주석
REQ_TAG_RE = re.compile(r"@(req|verifies|satisfies)\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)")

# @unit SCS-AF-002 -> SDD-AEB-501, SDD-AEB-602
#
# 추적성의 기본 방향은 하위 -> 상위다. 코드가 스스로 "나는 어느 설계를
# 구현했다"고 선언하게 만든다. ALM 쪽 association 과 대조해 양쪽이
# 어긋나면 verify_trace.py 가 잡는다.
UNIT_TAG_RE = re.compile(
    r"@unit\s+(SCS-[A-Z0-9]+-[A-Z0-9]+)\s*-+>\s*"
    r"([A-Z][A-Z0-9-]*(?:\s*,\s*[A-Z][A-Z0-9-]*)*)")
# 한 줄에 여러 ID 를 콤마로 나열한 경우도 잡는다
REQ_ID_RE = re.compile(r"\b((?:SRS|SYS|SWE)-[A-Z0-9]+-\d+)\b")

# C 함수 정의: 컬럼 0 에서 시작, 세미콜론으로 끝나지 않고, 괄호를 포함
C_FUNC_RE = re.compile(
    r"^(?!#)(?!\s)(?:[A-Za-z_][\w\s\*]*?\s+\*?)?([A-Za-z_]\w*)\s*\([^;]*$"
)
# GTest 테스트 케이스
TEST_F_RE = re.compile(r"^TEST(?:_F|_P)?\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)")
# pytest 테스트 함수
PY_FUNC_RE = re.compile(r"^def\s+(\w+)\s*\(")

C_KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof", "else", "do",
              "typedef", "struct", "union", "enum", "extern", "using", "namespace"}

# ctags 가 함수로 오인하는 테스트 프레임워크 매크로.
# `TEST_F(Suite, Name) {` 는 ctags 눈에 'TEST_F' 라는 함수 정의로 보인다.
# 그대로 두면 요구사항 페이지마다 'TEST_F' 가짜 행이 섞이고,
# 심볼 맵에서는 마지막 케이스가 앞의 것들을 덮어쓴다.
# 실제 테스트 이름은 TEST_F_RE 로 따로 잡으므로 여기서 버린다.
MACRO_NAMES = {
    "TEST", "TEST_F", "TEST_P", "TYPED_TEST", "TYPED_TEST_P",
    "INSTANTIATE_TEST_SUITE_P", "INSTANTIATE_TEST_CASE_P",
    "MOCK_METHOD", "EXPECT_CALL", "ON_CALL",
}


# --------------------------------------------------------------------------- #
def list_files():
    out = []
    for d in SEARCH_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p, dirs, fnames in os.walk(base):
            dirs[:] = [x for x in dirs if x not in EXCLUDE_DIRS]
            for fn in sorted(fnames):
                suf = Path(fn).suffix.lower()
                if suf in C_SUFFIXES or suf in PY_SUFFIXES:
                    out.append(Path(p) / fn)
    return out


def brace_end(lines, start_idx):
    """start_idx(0-based)부터 중괄호 균형이 맞는 줄을 찾아 1-based 라인 번호로 반환."""
    depth, opened = 0, False
    for j in range(start_idx, len(lines)):
        for ch in lines[j]:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
        if opened and depth == 0:
            return j + 1
    return start_idx + 1


def indent_end(lines, start_idx):
    """Python 함수의 끝을 들여쓰기로 판정."""
    base = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    last = start_idx
    for j in range(start_idx + 1, len(lines)):
        line = lines[j]
        if not line.strip():
            continue
        cur = len(line) - len(line.lstrip())
        if cur <= base:
            break
        last = j
    return last + 1


# --------------------------------------------------------------------------- #
def symbols_via_ctags(src: Path):
    """universal-ctags 로 함수 시작 라인을 얻는다. 실패 시 None."""
    if not shutil.which("ctags"):
        return None
    try:
        res = subprocess.run(
            ["ctags", "--fields=+n", "-x", "--c-kinds=f", str(src)],
            text=True, capture_output=True, check=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        print("[warn] ctags 실패 (%s) - 정규식으로 대체: %s" % (src.name, exc))
        return None

    starts = []
    line_re = re.compile(r"^(\w+)\s+\w+\s+(\d+)\s+(.+)$")
    for line in res.stdout.splitlines():
        m = line_re.match(line.strip())
        if m:
            starts.append((m.group(1), int(m.group(2))))
    return starts or None


def symbols_via_regex(src: Path, lines):
    """정규식 폴백. ctags 가 없는 환경(로컬 Windows 등)에서 쓰인다."""
    starts = []
    suf = src.suffix.lower()

    for i, line in enumerate(lines):
        if suf in PY_SUFFIXES:
            m = PY_FUNC_RE.match(line)
            if m:
                starts.append((m.group(1), i + 1))
            continue

        m = TEST_F_RE.match(line)
        if m:
            starts.append((m.group(2), i + 1))
            continue

        m = C_FUNC_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        if name in C_KEYWORDS:
            continue
        # 선언(프로토타입)이나 매크로 호출 제외: 이후 몇 줄 안에 '{' 가 와야 정의다
        window = " ".join(lines[i:i + 4])
        if ";" in window.split("{")[0] and "{" not in window:
            continue
        if "{" not in window:
            continue
        starts.append((name, i + 1))

    return starts


def collect_req_tags(lines, start_1based, end_1based, lookback=14, floor_1based=1):
    """함수 앞 문서 블록과 함수 본문에서 @req / @verifies 태그를 수집한다.

    `floor_1based` 는 **앞 심볼이 끝난 다음 줄**이다. 이게 없으면 위쪽
    lookback 이 앞 함수 영역까지 넘어가 그 함수의 태그를 빨아온다.
    Python 은 `@verifies` 가 `def` 아래 독스트링에 있어서 특히 잘 샜다 —
    앞 함수의 독스트링이 그대로 뒤 함수 것으로 잡혔다."""
    found = []

    # 함수 선언 위쪽 문서 블록 (앞 심볼 영역은 침범하지 않는다)
    top = max(0, start_1based - 1 - lookback, floor_1based - 1)
    for line in lines[top:start_1based - 1]:
        for kind, rid in REQ_TAG_RE.findall(line):
            found.append((kind, rid))

    # 함수 본문 내부 주석
    for line in lines[start_1based - 1:end_1based]:
        for kind, rid in REQ_TAG_RE.findall(line):
            found.append((kind, rid))

    # 중복 제거 (순서 유지)
    seen, out = set(), []
    for kind, rid in found:
        if (kind, rid) not in seen:
            seen.add((kind, rid))
            out.append((kind, rid))
    return out


def scan_units(unit_index, rel, lines, sym_ranges):
    """파일 전체에서 `@unit` 선언을 수집한다.

    심볼(함수)에 종속시키지 않는다. `@unit` 태그 자체가 유닛의 식별자이고,
    헤더의 typedef 나 파일 스코프 매크로처럼 함수가 아닌 선언에도 붙기 때문이다.
    마침 어떤 심볼 범위 안이거나 바로 앞이면 그 심볼도 기록한다 — 있으면
    줄 번호가 아닌 안정 링크를 걸 수 있다."""
    for i, line in enumerate(lines):
        m = UNIT_TAG_RE.search(line)
        if not m:
            continue
        uid = m.group(1)
        designs = [d.strip() for d in m.group(2).split(",") if d.strip()]
        ln = i + 1
        sym = next((r for r in sym_ranges if r[1] <= ln <= r[2]), None)
        if sym is None:
            # 선언 블록은 심볼 '앞'에 오므로 바로 뒤 심볼도 후보로 본다
            after = [r for r in sym_ranges if r[1] > ln]
            sym = min(after, key=lambda r: r[1]) if after else None
            if sym and sym[1] - ln > 14:      # 너무 멀면 남의 심볼이다
                sym = None
        unit_index[uid] = {
            "file": rel, "line": ln, "designs": designs,
            "symbol": sym[0] if sym else None,
            "unit_key": sym[3] if sym else None,
            "url": sym[4] if sym else
                   "https://github.com/%s/blob/%s/%s#L%d" % (REPO, BRANCH, rel, ln),
        }


def collect_unit_tag(lines, start_1based, end_1based, floor_1based=1):
    """`@unit` 선언 하나를 찾는다. (유닛 ID, [설계 ID]) 또는 None.

    범위 규칙은 collect_req_tags 와 같다 — 앞 심볼 영역을 침범하지 않는다.
    안 그러면 앞 함수의 선언을 뒤 함수 것으로 잡는다 (REVIEW.md D-7)."""
    top = max(0, start_1based - 1 - 14, floor_1based - 1)
    window = list(lines[top:start_1based - 1]) + list(lines[start_1based - 1:end_1based])
    for line in window:
        m = UNIT_TAG_RE.search(line)
        if m:
            designs = [d.strip() for d in m.group(2).split(",") if d.strip()]
            return m.group(1), designs
    return None


# --------------------------------------------------------------------------- #
def main():
    files = list_files()
    if not files:
        sys.stderr.write("인덱싱할 소스 파일이 없습니다. SEARCH_DIRS 를 확인하십시오.\n")
        return 1

    print("[info] %d개 파일 스캔 (%s)" % (len(files), ", ".join(SEARCH_DIRS)))
    print("[info] 대상 저장소: %s@%s" % (REPO, BRANCH))
    used_ctags = shutil.which("ctags") is not None
    print("[info] 심볼 추출: %s" % ("ctags" if used_ctags else "정규식 폴백 (ctags 없음)"))

    symbol_map = {}   # "src/x.c/func" -> url
    req_index = {}    # "SRS-AEB-305" -> [ {..} ]
    unit_index = {}   # "SCS-AF-002" -> {symbol, file, designs}
    rows = []         # CODE_INDEX.md 용

    for src in files:
        rel = src.relative_to(ROOT).as_posix()
        lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
        suf = src.suffix.lower()

        starts = None
        if suf in C_SUFFIXES:
            starts = symbols_via_ctags(src)
        if not starts:
            starts = symbols_via_regex(src, lines)

        # 매크로 오인 항목 제거 (ctags 경로에서만 나오지만 양쪽 모두 적용해 일관성 유지)
        dropped = [n for n, _ in starts if n in MACRO_NAMES]
        if dropped:
            print("[info] %s: 매크로 오인 심볼 %d개 제외 (%s)"
                  % (rel, len(dropped), ", ".join(sorted(set(dropped)))))
        starts = [(n, ln) for n, ln in starts if n not in MACRO_NAMES]

        # 실제 테스트 케이스 이름은 정규식으로 보강한다.
        # (ctags 는 TEST_F 매크로만 보고 케이스 이름을 모른다)
        if suf in C_SUFFIXES:
            known = {n for n, _ in starts}
            for i, line in enumerate(lines):
                m = TEST_F_RE.match(line)
                if m and m.group(2) not in known:
                    starts.append((m.group(2), i + 1))

        if not starts:
            # 함수가 없어도 @unit 선언은 있을 수 있다 (헤더의 typedef 등)
            scan_units(unit_index, rel, lines, [])
            print("[info] 심볼 없음: %s" % rel)
            continue

        prev_end = 0
        sym_ranges = []      # (심볼, 시작, 끝, key, url)
        for name, start in sorted(starts, key=lambda x: x[1]):
            if suf in PY_SUFFIXES:
                end = indent_end(lines, start - 1)
            else:
                end = brace_end(lines, start - 1)

            url = "https://github.com/%s/blob/%s/%s#L%d-L%d" % (REPO, BRANCH, rel, start, end)
            key = "%s/%s" % (rel, name)
            symbol_map[key] = url

            tags = collect_req_tags(lines, start, end, floor_1based=prev_end + 1)
            sym_ranges.append((name, start, end, key, url))
            prev_end = max(prev_end, end)
            for kind, rid in tags:
                req_index.setdefault(rid, []).append({
                    "kind": kind,          # req | verifies | satisfies
                    "symbol": name,
                    "file": rel,
                    "start": start,
                    "end": end,
                    "url": url,
                    "sym_path": "sym/%s" % key,
                })

            rows.append({
                "file": rel, "symbol": name, "start": start, "end": end,
                "reqs": [rid for _, rid in tags], "url": url,
                "sym_path": "sym/%s" % key,
            })
            print("[ok] %-58s L%-4d-%-4d %s"
                  % (key, start, end, ",".join(rid for _, rid in tags) or "-"))

        scan_units(unit_index, rel, lines, sym_ranges)

    # ---- 출력 ----
    (ROOT / "redirects_generated.json").write_text(
        json.dumps(symbol_map, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "req_index.json").write_text(
        json.dumps(req_index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (ROOT / "unit_index.json").write_text(
        json.dumps(unit_index, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")

    gen_dir = ROOT / "docs" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "CODE_INDEX.md").write_text(render_index(rows, req_index), encoding="utf-8")

    print("\n[done] 심볼 %d개 / 요구사항 %d개 / 유닛 선언 %d개 인덱싱"
          % (len(symbol_map), len(req_index), len(unit_index)))
    print("       redirects_generated.json, req_index.json, docs/generated/CODE_INDEX.md")
    return 0


def render_index(rows, req_index):
    base = "https://%s.github.io/%s" % tuple(REPO.split("/"))
    out = [
        "# 소스 코드 인덱스 (자동 생성)",
        "",
        "> `scripts/build_symbol_map.py` 가 생성한다. 직접 수정하지 말 것.",
        "> 라인 번호는 생성 시점 기준이며, 링크는 심볼 이름 기준이라 라인이 바뀌어도 유효하다.",
        "> 저장소에 커밋된 파일은 스냅샷이다. 최신본은 CI 아티팩트(`code-index`)와 GitHub Pages 를 보라.",
        "",
        "- 대상: `%s` @ `%s`" % (REPO, BRANCH),
        "- **Base URL**: %s — 아래 링크는 이 주소 기준 상대 경로다." % base,
        "- 안정 링크 형식: `%s/sym/<경로>/<심볼>/`" % base,
        "- 요구사항 링크 형식: `%s/req/<요구사항ID>/`" % base,
        "",
        "## 1. 요구사항 → 코드 (ALM 에 걸 링크)",
        "",
        "| 요구사항 | 관계 | 심볼 | 위치 | 안정 링크 |",
        "|---|---|---|---|---|",
    ]
    for rid in sorted(req_index):
        for e in req_index[rid]:
            rel_kind = {"req": "구현", "verifies": "검증", "satisfies": "충족"}.get(e["kind"], e["kind"])
            out.append("| `%s` | %s | `%s` | %s:%d-%d | `req/%s/` |"
                       % (rid, rel_kind, e["symbol"], e["file"], e["start"], e["end"], rid))
    if not req_index:
        out.append("| (없음) | | | | |")

    # ---- 추적성 갭: 인덱스에서 자동 도출된다 ----
    gaps = []
    for rid in sorted(req_index):
        impl = [e for e in req_index[rid] if e["kind"] in ("req", "satisfies")]
        ver = [e for e in req_index[rid] if e["kind"] == "verifies"]
        if impl and not ver:
            gaps.append((rid, "검증 없음", "구현은 있으나 이를 검증하는 테스트가 없다"))
        elif ver and not impl:
            gaps.append((rid, "고아 테스트", "테스트는 있으나 구현에 @req 표기가 없다 (요구사항 미승인 가능)"))

    out += ["", "## 2. 추적성 갭 (자동 도출)", ""]
    if gaps:
        out += ["| 요구사항 | 갭 | 설명 |", "|---|---|---|"]
        out += ["| `%s` | **%s** | %s |" % g for g in gaps]
    else:
        out.append("갭 없음 — 모든 요구사항에 구현과 검증이 모두 연결되어 있다.")

    out += ["", "## 3. 전체 심볼", "",
            "| 파일 | 심볼 | 라인 | 요구사항 | 안정 링크 |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["file"], x["start"])):
        out.append("| `%s` | `%s` | %d-%d | %s | `%s/` |"
                   % (r["file"], r["symbol"], r["start"], r["end"],
                      ", ".join("`%s`" % x for x in r["reqs"]) or "-",
                      r["sym_path"]))
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
