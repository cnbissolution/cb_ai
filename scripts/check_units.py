#!/usr/bin/env python3
"""소스의 모든 정의부가 유닛으로 선언되었는지 검사한다.

`verify_trace.py` 는 ALM 에 링크가 있는지 본다. 이 스크립트는 그 **앞 단계**를
본다 — 애초에 코드가 유닛으로 선언조차 되지 않았다면 ALM 링크가 있을 리 없고,
"미확보"로도 안 잡힌다. 그 사각지대를 없앤다.

Codebeamer 없이 돈다. 자격증명이 필요 없어 PR 검사에 넣기 좋다.

## 무엇을 유닛으로 보는가

  구현 유닛   함수 정의            -> 동적시험 대상
  선언 유닛   typedef / #define / 전역·static 변수
                                   -> 단독으로 동적시험이 안 된다

선언 유닛은 초기화 함수 등 **다른 유닛과 함께 검증**된다. 그 주체를
`@verified_by` 로 명시하게 한다. 명시가 없으면 "검증 주체 불명"으로 잡는다.
어딘가에서 검증되고 있다는 근거 없이 유닛만 선언해 두면, 추적성 표는 채워지는데
실제로는 아무도 확인하지 않는 상태가 된다.

## 주석 형식

    @unit        SCS-AF-002 -> SDD-AEB-501, SDD-AEB-602
    @verified_by SCS-AF-001        (선언 유닛만)

사용:
    python scripts/check_units.py
    python scripts/check_units.py --dirs src --allow-missing-verifier

종료 코드: 선언 안 된 정의부나 검증 주체 불명 유닛이 있으면 1.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

C_SUFFIXES = {".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"}

UNIT_RE = re.compile(r"@unit\s+(SCS-[A-Z0-9]+-[A-Z0-9]+)")
# 파일 단위 범위 제외. 벤더 제공 헤더처럼 우리 유닛이 아닌 것을 위한 장치다.
# 조용히 빼지 않고 결과에 "범위 밖"으로 드러낸다 — 숨기면 잊힌다.
SCOPE_EXCLUDE_RE = re.compile(r"@unit_scope\s+exclude\b[ \t]*(.*)")
# `none` 은 "검증 주체가 없다"를 명시적으로 선언하는 값이다.
# 미사용 정의처럼 실제로 아무도 검증하지 않는 것을 억지로 다른 유닛에
# 매달지 않기 위해 둔다. 통과시키되 따로 센다.
VERIFIED_BY_RE = re.compile(
    r"@verified_by\s+(SCS-[A-Z0-9]+-[A-Z0-9]+|none)\b")

# 정의부 판정
FUNC_RE = re.compile(r"^(?!#)(?!\s)(?:[A-Za-z_][\w\s\*]*?\s+\*?)?([A-Za-z_]\w*)\s*\([^;]*$")
TYPEDEF_RE = re.compile(r"^typedef\b")
DEFINE_RE = re.compile(r"^#\s*define\s+(\w+)")
GLOBAL_RE = re.compile(r"^(?:static\s+)?[A-Za-z_][\w\s\*]*\s+\*?(\w+)\s*(?:=[^=]|;)")

C_KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof", "else", "do",
              "typedef", "struct", "union", "enum", "extern", "using", "namespace"}

# 헤더 가드처럼 유닛으로 볼 필요가 없는 것
GUARD_RE = re.compile(r"^#\s*define\s+\w*_H\b|^#\s*define\s+\w*_H$")


def scan_file(path: Path, rel: str):
    """(정의부 목록, 유닛 선언 목록) 을 돌려준다.

    정의부: (종류, 이름, 줄번호)
    유닛:   (유닛ID, 줄번호, verified_by 또는 None)
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    # 파일 상단 20줄 안의 범위 제외 선언
    for raw in lines[:20]:
        m = SCOPE_EXCLUDE_RE.search(raw)
        if m:
            return None, (m.group(1) or "").strip(" *")

    defs, units = [], []

    in_define_run = False
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        ln = i + 1

        m = UNIT_RE.search(line)
        if m:
            # 같은 주석 블록 안의 @verified_by 를 찾는다 (앞뒤 6줄)
            window = "\n".join(lines[max(0, i - 6):i + 7])
            vb = VERIFIED_BY_RE.search(window)
            units.append((m.group(1), ln, vb.group(1) if vb else None))
            continue

        if not line or line.lstrip().startswith(("*", "//", "/*")):
            continue

        # #define 은 연속 구간을 하나의 정의부로 센다
        if DEFINE_RE.match(line):
            if GUARD_RE.match(line):
                continue
            if not in_define_run:
                defs.append(("define", DEFINE_RE.match(line).group(1), ln))
                in_define_run = True
            continue
        if line.startswith("#"):
            continue
        in_define_run = False

        if TYPEDEF_RE.match(line):
            defs.append(("typedef", line[:40].strip(), ln))
            continue

        m = FUNC_RE.match(line)
        if m and m.group(1) not in C_KEYWORDS:
            window = " ".join(lines[i:i + 4])
            if "{" in window:
                defs.append(("function", m.group(1), ln))
                continue

        m = GLOBAL_RE.match(line)
        if m and m.group(1) not in C_KEYWORDS and "(" not in line:
            defs.append(("global", m.group(1), ln))

    return (defs, units), None


def covering_unit(units, def_line, lookback=20):
    """정의부 앞쪽에서 가장 가까운 유닛 선언을 찾는다.

    선언 블록은 정의부 '위'에 온다. 다른 정의부를 건너뛰지 않도록
    lookback 을 좁게 잡는다."""
    cands = [u for u in units if 0 < def_line - u[1] <= lookback]
    return max(cands, key=lambda u: u[1]) if cands else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dirs", nargs="*", default=["src"],
                    help="검사할 디렉터리 (기본 src)")
    ap.add_argument("--allow-missing-verifier", action="store_true",
                    help="선언 유닛의 @verified_by 누락을 실패로 보지 않는다")
    args = ap.parse_args()

    files = []
    for d in args.dirs:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p, dirs, names in os.walk(base):
            for fn in sorted(names):
                if Path(fn).suffix.lower() in C_SUFFIXES:
                    files.append(Path(p) / fn)

    undeclared, unverified, ok, excluded = [], [], [], []
    unverified_none = []   # @verified_by none 으로 밝힌 것
    for path in sorted(files):
        rel = path.relative_to(ROOT).as_posix()
        result, reason = scan_file(path, rel)
        if result is None:
            excluded.append((rel, reason))
            continue
        defs, units = result
        for kind, name, ln in defs:
            u = covering_unit(units, ln)
            if u is None:
                undeclared.append((rel, kind, name, ln))
                continue
            uid, _, vb = u
            ok.append((rel, kind, name, uid))
            # 함수가 아닌 정의부는 단독으로 동적시험이 안 된다.
            # 어느 유닛과 함께 검증되는지 근거가 있어야 한다
            if kind != "function":
                if not vb:
                    unverified.append((rel, kind, name, uid))
                elif vb == "none":
                    unverified_none.append((rel, kind, name, uid))

    print("=" * 76)
    print(" 유닛 선언 검사 — %d개 정의부" % (len(ok) + len(undeclared)))
    print("=" * 76)

    if excluded:
        print("\n[범위 밖] @unit_scope exclude 로 제외됨 (%d건)" % len(excluded))
        for rel, reason in excluded:
            print("   %-26s %s" % (rel, reason or "(사유 없음)"))

    if undeclared:
        print("\n[선언 안 됨] @unit 이 없는 정의부 (%d건)" % len(undeclared))
        for rel, kind, name, ln in undeclared:
            print("   %-26s %-9s %-28s L%d" % (rel, kind, name[:28], ln))

    if unverified:
        print("\n[검증 주체 불명] 선언 유닛인데 @verified_by 가 없다 (%d건)"
              % len(unverified))
        print("   단독으로 동적시험이 안 되는 정의부다. 어느 유닛과 함께")
        print("   검증되는지 밝혀야 한다 (예: 초기화 함수).")
        for rel, kind, name, uid in unverified:
            print("   %-26s %-9s %-24s %s" % (rel, kind, name[:24], uid))

    if unverified_none:
        print("\n[미검증 — 사유 기재] @verified_by none (%d건)"
              % len(unverified_none))
        print("   아무도 동적으로 검증하지 않는다. 설계 항목이 유지 사유를")
        print("   기술하고 있어야 한다.")
        for rel, kind, name, uid in unverified_none:
            print("   %-26s %-9s %-24s %s" % (rel, kind, name[:24], uid))

    print("\n" + "=" * 76)
    print(" 선언됨 %d / 선언 안 됨 %d / 검증 주체 불명 %d / 미검증(사유 기재) %d"
          % (len(ok), len(undeclared), len(unverified), len(unverified_none)))
    print("=" * 76)

    bad = bool(undeclared) or (bool(unverified) and not args.allow_missing_verifier)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
