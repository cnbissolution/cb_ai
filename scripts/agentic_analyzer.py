#!/usr/bin/env python3
"""
Agentic AI 실패 분석기 — CI 실패/커버리지 미달 시 원인을 분석해 Codebeamer 에 기록.

파이프라인이 붉게 물든 순간, 개발자가 로그를 파헤치기 전에 에이전트가
  1) 실패한 테스트와 커버리지 갭을 수집하고
  2) 관련 소스 코드와 함께 Claude 에 구조화 분석을 요청하고
  3) 결과를 Codebeamer 항목의 코멘트로 남겨
ALM 안에서 원인/조치/영향 요구사항이 바로 보이게 한다.

사용:
  python3 scripts/agentic_analyzer.py \
      --test-report unit_report.xml \
      --func-report functional_report.xml \
      --coverage coverage_report.xml \
      --source-dir src \
      --item-id 10254 \
      --build-url https://github.com/org/repo/actions/runs/123

환경변수:
  ANTHROPIC_API_KEY   Claude API 키
  CB_URL              Codebeamer 베이스 URL (예: https://cb.example.com/cb)
  CB_TOKEN            Personal Access Token (또는 CB_USER/CB_PASS)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

import requests

TIMEOUT = 60
MODEL = "claude-opus-5"
MAX_SOURCE_CHARS = 60_000  # 프롬프트에 실을 소스 코드 총량 상한

# 소스 코드 확장자 화이트리스트
SOURCE_EXT = (".c", ".h", ".cpp", ".hpp")

# --------------------------------------------------------------------------- #
# 분석 결과 스키마 — 구조화 출력으로 강제하여 코멘트 서식을 일관되게 유지한다
# --------------------------------------------------------------------------- #
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "한 문장 요약 (한국어)",
        },
        "root_cause": {
            "type": "string",
            "description": "실패의 근본 원인. 코드 위치와 논리적 인과를 포함 (한국어)",
        },
        "defect_category": {
            "type": "string",
            "enum": [
                "requirement_mismatch",     # 요구사항과 코드 불일치
                "test_defect",              # 테스트 코드 자체의 결함
                "logic_error",              # 제어 로직 오류
                "missing_defensive_code",   # 방어 코드 누락
                "dead_code",                # 도달 불가 코드
                "coverage_gap",             # 커버리지 미달
                "build_config",             # 빌드/환경 설정 문제
            ],
        },
        "affected_file": {"type": "string"},
        "affected_line": {"type": "integer"},
        "related_requirement_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "관련 SRS ID 목록 (예: SRS-AEB-305)",
        },
        "suggested_fix": {
            "type": "string",
            "description": "조치 방안 설명 (한국어)",
        },
        "suggested_patch": {
            "type": "string",
            "description": "As-Is / To-Be 형태의 C 코드 스니펫. 코드 외 설명 금지",
        },
        "recommended_action": {
            "type": "string",
            "enum": ["create_bug", "update_requirement", "fix_test",
                     "add_test_case", "no_action"],
        },
        "confidence": {
            "type": "number",
            "description": "분석 신뢰도 0.0 ~ 1.0",
        },
    },
    "required": [
        "summary", "root_cause", "defect_category", "affected_file",
        "related_requirement_ids", "suggested_fix", "suggested_patch",
        "recommended_action", "confidence",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
당신은 ISO 26262 / ASPICE 환경에서 자동차 전장 C 코드를 검증하는 시니어 소프트웨어 \
안전 엔지니어다. CI 파이프라인의 시험 실패와 커버리지 리포트를 받아 근본 원인을 규명한다.

분석 원칙:
- 로그에 나타난 사실과 제공된 소스 코드만 근거로 삼는다. 추측은 confidence 로 표현한다.
- 테스트가 틀린 경우와 코드가 틀린 경우를 반드시 구분한다. 요구사항이 코드보다 \
  넓은 범위를 요구하고 있다면 requirement_mismatch 로 분류한다.
- 통과했지만 의도한 로직을 검증하지 못하는 테스트(가짜 통과)나, 가드 조건 때문에 \
  도달할 수 없는 방어 코드를 발견하면 반드시 지적한다.
- suggested_patch 는 실제 컴파일 가능한 C 스니펫으로 작성하고, 주석으로 As-Is / To-Be 를 표시한다.
- 모든 서술은 한국어로 작성한다."""


# --------------------------------------------------------------------------- #
# 증적 수집
# --------------------------------------------------------------------------- #
def collect_failures(path, label):
    """JUnit XML 에서 실패/오류 케이스만 추출."""
    if not path or not os.path.exists(path):
        return []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        print("[warn] %s 파싱 실패: %s" % (path, exc))
        return []

    failures = []
    for tc in root.iter("testcase"):
        node = tc.find("failure")
        if node is None:
            node = tc.find("error")
        if node is None:
            continue
        failures.append({
            "suite": label,
            "test_name": tc.get("name") or "(unnamed)",
            "classname": tc.get("classname") or "",
            "message": (node.get("message") or "").strip(),
            "detail": (node.text or "").strip()[:3000],
        })
    print("[ok] %s: 실패 %d건 수집" % (label, len(failures)))
    return failures


def collect_coverage_gaps(path, threshold_line=80.0, threshold_branch=70.0):
    """Cobertura XML 에서 전체 커버리지율과 미커버 라인을 추출."""
    if not path or not os.path.exists(path):
        return None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        print("[warn] 커버리지 파싱 실패: %s" % exc)
        return None

    def rate(attr):
        try:
            return round(float(root.get(attr, 0)) * 100.0, 2)
        except ValueError:
            return 0.0

    uncovered = []
    for cls in root.iter("class"):
        fname = cls.get("filename") or cls.get("name") or "?"
        for line in cls.iter("line"):
            if line.get("hits") == "0":
                uncovered.append("%s:%s" % (fname, line.get("number")))
            elif line.get("branch") == "true":
                cond = line.get("condition-coverage") or ""
                if cond and not cond.startswith("100%"):
                    uncovered.append("%s:%s (branch %s)"
                                     % (fname, line.get("number"), cond))

    gaps = {
        "line_rate": rate("line-rate"),
        "branch_rate": rate("branch-rate"),
        "line_threshold": threshold_line,
        "branch_threshold": threshold_branch,
        "below_threshold": (rate("line-rate") < threshold_line
                            or rate("branch-rate") < threshold_branch),
        "uncovered": uncovered[:80],
    }
    print("[ok] 커버리지: line %s%% / branch %s%% (미커버 %d개소)"
          % (gaps["line_rate"], gaps["branch_rate"], len(uncovered)))
    return gaps


def load_sources(source_dir, extra_files=()):
    """분석 컨텍스트로 실을 소스 코드를 읽는다. 총량을 상한으로 제한한다."""
    paths = []
    if source_dir and os.path.isdir(source_dir):
        for base, _dirs, files in os.walk(source_dir):
            for fn in sorted(files):
                if fn.endswith(SOURCE_EXT):
                    paths.append(os.path.join(base, fn))
    paths.extend(p for p in extra_files if p and os.path.exists(p))

    chunks, total = [], 0
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError as exc:
            print("[warn] 소스 읽기 실패 %s: %s" % (p, exc))
            continue
        if total + len(body) > MAX_SOURCE_CHARS:
            print("[warn] 소스 총량 상한 초과 - %s 이후 생략" % p)
            break
        # 라인 번호를 붙여 LLM 이 affected_line 을 정확히 지목할 수 있게 한다
        numbered = "\n".join("%4d | %s" % (i, ln)
                             for i, ln in enumerate(body.splitlines(), 1))
        chunks.append("===== FILE: %s =====\n%s" % (p.replace("\\", "/"), numbered))
        total += len(body)

    print("[ok] 소스 %d개 파일 / %d chars 로드" % (len(chunks), total))
    return "\n\n".join(chunks)


# --------------------------------------------------------------------------- #
# Claude 분석
# --------------------------------------------------------------------------- #
def build_user_prompt(failures, gaps, sources, build_url):
    parts = []
    if failures:
        parts.append("## 실패한 시험 (%d건)\n" % len(failures))
        for i, f in enumerate(failures, 1):
            parts.append(
                "### %d. [%s] %s\n- 메시지: %s\n- 상세:\n```\n%s\n```"
                % (i, f["suite"], f["test_name"], f["message"], f["detail"])
            )
    else:
        parts.append("## 실패한 시험 없음 (커버리지 미달로 트리거됨)")

    if gaps:
        parts.append(
            "\n## 커버리지\n- Line: %s%% (임계 %s%%)\n- Branch: %s%% (임계 %s%%)\n"
            "- 미커버 지점:\n```\n%s\n```"
            % (gaps["line_rate"], gaps["line_threshold"],
               gaps["branch_rate"], gaps["branch_threshold"],
               "\n".join(gaps["uncovered"]) or "(없음)")
        )

    if build_url:
        parts.append("\n## 빌드\n%s" % build_url)

    parts.append("\n## 소스 코드 (좌측은 라인 번호)\n%s" % sources)
    parts.append(
        "\n위 정보를 근거로 근본 원인을 규명하고 스키마에 맞춰 분석 결과를 반환하라."
    )
    return "\n".join(parts)


def analyze(prompt, dry_run=False):
    """Claude 로 구조화 분석을 수행한다."""
    if dry_run:
        print("[dry-run] Claude 호출 생략. 프롬프트 %d chars" % len(prompt))
        return {
            "summary": "(dry-run) 분석 미수행",
            "root_cause": "(dry-run)",
            "defect_category": "test_defect",
            "affected_file": "-",
            "affected_line": 0,
            "related_requirement_ids": [],
            "suggested_fix": "(dry-run)",
            "suggested_patch": "/* dry-run */",
            "recommended_action": "no_action",
            "confidence": 0.0,
        }

    import anthropic

    client = anthropic.Anthropic()
    request = {
        "model": MODEL,
        "max_tokens": 16000,
        "system": SYSTEM_PROMPT,
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": "high",
            "format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA},
        },
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        # 안전 분류기가 요청을 거절하는 경우 서버측 폴백으로 자동 우회
        resp = client.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **request
        )
    except anthropic.BadRequestError as exc:
        # 폴백/베타 조합이 거부되면 폴백 없이 재시도
        print("[warn] 서버측 폴백 사용 불가 (%s) - 폴백 없이 재시도" % exc.message)
        resp = client.messages.create(**request)
    except anthropic.AuthenticationError:
        raise SystemExit("ANTHROPIC_API_KEY 가 유효하지 않습니다.")
    except anthropic.RateLimitError as exc:
        retry_after = exc.response.headers.get("retry-after", "60")
        raise SystemExit("레이트 리밋. %s초 후 재시도하십시오." % retry_after)
    except anthropic.APIConnectionError:
        raise SystemExit("Claude API 연결 실패. 네트워크를 확인하십시오.")

    if resp.stop_reason == "refusal":
        detail = getattr(resp, "stop_details", None)
        raise SystemExit("모델이 요청을 거절했습니다: %s"
                         % (getattr(detail, "category", "unknown")))

    text = next((b.text for b in resp.content if b.type == "text"), None)
    if not text:
        raise SystemExit("분석 결과 텍스트가 비어 있습니다.")
    return json.loads(text)


# --------------------------------------------------------------------------- #
# Codebeamer 코멘트 등록
# --------------------------------------------------------------------------- #
CATEGORY_LABEL = {
    "requirement_mismatch": "요구사항-코드 불일치",
    "test_defect": "테스트 코드 결함",
    "logic_error": "제어 로직 오류",
    "missing_defensive_code": "방어 코드 누락",
    "dead_code": "도달 불가 코드",
    "coverage_gap": "커버리지 미달",
    "build_config": "빌드/환경 설정",
}

ACTION_LABEL = {
    "create_bug": "결함(Bug) 항목 신규 등록",
    "update_requirement": "요구사항 수정/추가",
    "fix_test": "테스트 코드 수정",
    "add_test_case": "테스트 케이스 추가",
    "no_action": "조치 불필요",
}


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_html(analysis, build_url):
    """Codebeamer 코멘트용 HTML 조립. commentFormat="Html" 로 전송한다."""
    reqs = ", ".join(analysis.get("related_requirement_ids") or []) or "-"
    cat = analysis.get("defect_category", "")
    act = analysis.get("recommended_action", "")

    return (
        "<h4>AI Agent 자동 실패 분석</h4>"
        "<table border='1' cellpadding='4'>"
        "<tr><td><b>요약</b></td><td>%s</td></tr>"
        "<tr><td><b>결함 유형</b></td><td>%s</td></tr>"
        "<tr><td><b>위치</b></td><td>%s%s</td></tr>"
        "<tr><td><b>관련 요구사항</b></td><td>%s</td></tr>"
        "<tr><td><b>권고 조치</b></td><td>%s</td></tr>"
        "<tr><td><b>신뢰도</b></td><td>%.2f</td></tr>"
        "</table>"
        "<h5>근본 원인</h5><p>%s</p>"
        "<h5>조치 방안</h5><p>%s</p>"
        "<h5>제안 패치</h5><pre>%s</pre>"
        "<p><i>Build: %s</i></p>"
        % (
            _esc(analysis.get("summary", "")),
            _esc(CATEGORY_LABEL.get(cat, cat)),
            _esc(analysis.get("affected_file", "-")),
            (":%s" % analysis["affected_line"]) if analysis.get("affected_line") else "",
            _esc(reqs),
            _esc(ACTION_LABEL.get(act, act)),
            float(analysis.get("confidence", 0.0)),
            _esc(analysis.get("root_cause", "")),
            _esc(analysis.get("suggested_fix", "")),
            _esc(analysis.get("suggested_patch", "")),
            _esc(build_url or "-"),
        )
    )


def post_comment(base_url, item_id, html, dry_run=False):
    """POST /api/v3/items/{itemId}/comments

    주의: payload 의 {"format": "Markdown"} 은 유효하지 않다.
    Codebeamer 는 commentFormat 필드에 Html / Wiki / PlainText 만 허용한다."""
    if dry_run or not item_id:
        print("[dry-run] Codebeamer 코멘트 등록 생략 (item_id=%s)" % item_id)
        print(html[:1500])
        return 0

    token = os.environ.get("CB_TOKEN")
    user, password = os.environ.get("CB_USER"), os.environ.get("CB_PASS")
    headers = {"Accept": "application/json"}
    auth = None
    if token:
        headers["Authorization"] = "Bearer %s" % token
    elif user and password:
        auth = (user, password)
    else:
        sys.stderr.write("Codebeamer 인증 정보 없음 - 코멘트 등록 생략\n")
        return 1

    url = "%s/api/v3/items/%s/comments" % (base_url.rstrip("/"), item_id)
    resp = requests.post(
        url,
        json={"comment": html, "commentFormat": "Html"},
        headers=headers, auth=auth, timeout=TIMEOUT,
    )
    if not resp.ok:
        sys.stderr.write("[FAIL] 코멘트 등록 실패: HTTP %d\n%s\n"
                         % (resp.status_code, resp.text[:500]))
        return 1

    print("[ok] Codebeamer 항목 #%s 에 AI 분석 코멘트 등록 완료" % item_id)
    return 0


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="CI 실패를 AI 로 분석해 Codebeamer 에 기록")
    ap.add_argument("--test-report", help="단위 시험 JUnit XML")
    ap.add_argument("--func-report", help="기능 시험 JUnit XML")
    ap.add_argument("--coverage", help="gcovr Cobertura XML")
    ap.add_argument("--source-dir", default="src", help="분석 대상 소스 디렉토리")
    ap.add_argument("--include-test-source", action="store_true",
                    help="테스트 소스도 컨텍스트에 포함 (테스트 결함 판별에 유용)")
    ap.add_argument("--item-id", default="", help="코멘트를 남길 Codebeamer 항목 ID")
    ap.add_argument("--build-url", default="", help="CI 빌드 URL")
    ap.add_argument("--dry-run", action="store_true",
                    help="Claude/Codebeamer 호출 없이 프롬프트와 렌더링만 확인")
    ap.add_argument("--save-analysis", help="분석 결과 JSON 저장 경로")
    args = ap.parse_args()

    failures = (collect_failures(args.test_report, "Unit Test")
                + collect_failures(args.func_report, "Functional Test"))
    gaps = collect_coverage_gaps(args.coverage)

    if not failures and not (gaps and gaps["below_threshold"]):
        print("[skip] 실패도 커버리지 미달도 없습니다. 분석할 대상이 없습니다.")
        return 0

    extra = []
    if args.include_test_source:
        extra = [p for p in ("test/test_Aeb_FusionEngine.cpp",
                             "test/test_functional_scenario.py") if os.path.exists(p)]
    sources = load_sources(args.source_dir, extra)

    prompt = build_user_prompt(failures, gaps, sources, args.build_url)
    analysis = analyze(prompt, dry_run=args.dry_run)

    print("\n--- 분석 결과 ---")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))

    if args.save_analysis:
        with open(args.save_analysis, "w", encoding="utf-8") as fh:
            json.dump(analysis, fh, indent=2, ensure_ascii=False)
        print("[ok] 분석 결과 저장: %s" % args.save_analysis)

    base_url = os.environ.get("CB_URL", "")
    html = render_html(analysis, args.build_url)
    return post_comment(base_url, args.item_id, html, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
