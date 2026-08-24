#!/usr/bin/env python3
"""
CI 파이프라인 결과(JUnit XML + 커버리지)를 Codebeamer 로 전송한다.

Jenkins 플러그인이나 Codebeamer Extension 개발 없이, 표준 REST API 만으로
Test Run 을 생성하고 Test Case 항목과 연결하여 추적성을 확보하는 것이 목적이다.

사용:
  python3 scripts/upload_to_codebeamer.py \
      --unit-report unit_report.xml \
      --func-report functional_report.xml \
      --coverage coverage_report.xml \
      --build-ref 1234/56 --commit abc1234

환경변수:
  CB_URL                    예: https://codebeamer.example.com/cb
  CB_TOKEN                  Personal Access Token (권장)
  CB_USER / CB_PASS         Basic 인증 (CB_TOKEN 미설정 시 대체)
  CB_TEST_RUN_TRACKER_ID    Test Run 트래커 ID
  CB_TEST_CASE_TRACKER_ID   Test Case 트래커 ID (필수 - 아래 참조)

엔드포인트:
  Test Run 생성은 일반 항목 생성(/trackers/{id}/items)이 아니라 테스트 실행 전용
  엔드포인트를 쓴다. CI 자동화 결과는 /trackers/{id}/automatedtestruns 가 대상이다.

필드 매핑 (실측 스키마 기준, Automotive Template 3.0 tracker 123469):
  status     워크플로 상태  Unset / In progress / Suspended / Finished / Closed / ...
  result     시험 결과      Unset / Passed / Failed / Blocked / Partly Passed / ...
  build      빌드 식별자    전용 TextField
  testCases  Test Case 표   **필수 필드** - 매칭되는 Test Case 없이는 생성 거부됨

  Passed/Failed 는 result 로 보내야 한다. status 에는 그런 옵션이 없다.
  이 때문에 CB_TEST_CASE_TRACKER_ID 는 선택이 아니라 사실상 필수다.

전송 전 확인:
  python3 scripts/upload_to_codebeamer.py --check-schema
  대상 인스턴스의 실제 옵션 이름과 대조한다 (다국어 인스턴스는 로컬라이즈됨).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 30

# Codebeamer Test Run 트래커는 '상태(Status)'와 '결과(Result)'가 별개 필드다.
# 실측 스키마(Automotive Template 3.0, tracker 123469) 기준:
#   Status (id 7)  : Unset / In progress / Suspended / Finished / Closed /
#                    To be approved / Ready for execution / Rejected
#   Result (id 15) : Unset / Passed / Failed / Blocked / Partly Passed /
#                    Not Applicable / NOT RUN YET
# Passed/Failed 를 Status 에 보내면 유효한 옵션이 아니라 거부된다.
RESULT_PASSED = "Passed"
RESULT_FAILED = "Failed"
RESULT_BLOCKED = "Blocked"

# 자동화 실행이 끝난 Test Run 의 워크플로 상태
RUN_STATUS_DONE = "Finished"

# 다국어 인스턴스는 옵션 이름이 로컬라이즈될 수 있다.
# --check-schema 로 실제 옵션 이름을 먼저 확인할 것.


@dataclass
class TestResult:
    name: str
    classname: str
    status: str
    duration_ms: int = 0
    message: str = ""


@dataclass
class Suite:
    label: str
    results: list = field(default_factory=list)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == RESULT_FAILED)

    @property
    def overall_result(self) -> str:
        """Test Run 의 Result 필드에 넣을 값 (Status 아님)."""
        return RESULT_FAILED if self.failed else RESULT_PASSED


# --------------------------------------------------------------------------- #
# JUnit XML 파싱
# --------------------------------------------------------------------------- #
def parse_junit(path, label):
    """GTest / pytest 가 생성한 JUnit XML 을 공통 구조로 파싱한다."""
    if not path or not os.path.exists(path):
        print("[skip] %s: 리포트 파일 없음 (%s)" % (label, path))
        return None

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        print("[warn] %s: XML 파싱 실패 - %s" % (label, exc))
        return None

    suite = Suite(label=label)
    for tc in root.iter("testcase"):
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")

        if failure is not None or error is not None:
            node = failure if failure is not None else error
            status = RESULT_FAILED
            message = (node.get("message") or "") + "\n" + (node.text or "")
        elif skipped is not None:
            status = RESULT_BLOCKED
            message = skipped.get("message") or ""
        else:
            status = RESULT_PASSED
            message = ""

        try:
            duration_ms = int(float(tc.get("time") or 0) * 1000)
        except ValueError:
            duration_ms = 0

        suite.results.append(
            TestResult(
                name=tc.get("name") or "(unnamed)",
                classname=tc.get("classname") or "",
                status=status,
                duration_ms=duration_ms,
                message=message.strip()[:4000],
            )
        )

    print("[ok] %s: %d건 파싱 (실패 %d건)" % (label, len(suite.results), suite.failed))
    return suite


def parse_coverage(path):
    """gcovr Cobertura XML 에서 라인/브랜치 커버리지율을 추출한다."""
    if not path or not os.path.exists(path):
        return None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        print("[warn] 커버리지 XML 파싱 실패 - %s" % exc)
        return None

    def pct(attr):
        try:
            return round(float(root.get(attr, 0)) * 100.0, 2)
        except ValueError:
            return 0.0

    cov = {"line": pct("line-rate"), "branch": pct("branch-rate")}
    print("[ok] 커버리지: line %s%% / branch %s%%" % (cov["line"], cov["branch"]))
    return cov


# --------------------------------------------------------------------------- #
# Codebeamer 클라이언트
# --------------------------------------------------------------------------- #
class CodebeamerClient:
    def __init__(self, base_url, token, user, password, dry_run=False):
        self.base = base_url.rstrip("/")
        self.dry_run = dry_run
        self.s = requests.Session()

        if token:
            self.s.headers["Authorization"] = "Bearer %s" % token
        elif user and password:
            self.s.auth = (user, password)
        elif not dry_run:
            raise SystemExit("인증 정보 없음: CB_TOKEN 또는 CB_USER/CB_PASS 를 설정하십시오.")

        self.s.headers["Accept"] = "application/json"
        retry = Retry(total=3, backoff_factor=1.0,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET", "POST", "PUT"])
        self.s.mount("https://", HTTPAdapter(max_retries=retry))
        self.s.mount("http://", HTTPAdapter(max_retries=retry))

    def _url(self, path):
        return "%s/api/v3%s" % (self.base, path)

    def _check(self, resp, what):
        """상태코드를 반드시 확인한다. 확인 없이 json()['id'] 에 접근하면
        실패 시 KeyError 로 엉뚱한 지점에서 파이프라인이 죽는다."""
        if not resp.ok:
            sys.stderr.write("[FAIL] %s: HTTP %d\n" % (what, resp.status_code))
            sys.stderr.write("        %s\n" % resp.text[:1000])
            resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return {}

    def find_test_case_ids(self, tracker_id):
        """Test Case 트래커의 항목명 -> ID 매핑을 조회한다.
        자동화 테스트 함수명을 Test Case 항목명과 맞춰 두면 추적성이 자동 연결된다."""
        if not tracker_id:
            print("[info] CB_TEST_CASE_TRACKER_ID 미설정 - Test Case 링크 생략")
            return {}
        mapping = {}
        page = 1
        while True:
            resp = self.s.get(self._url("/trackers/%s/items" % tracker_id),
                              params={"page": page, "pageSize": 100}, timeout=TIMEOUT)
            data = self._check(resp, "Test Case 목록 조회")
            items = data.get("items", [])
            if not items:
                break
            for it in items:
                if it.get("name"):
                    mapping[it["name"]] = it["id"]
            if page * 100 >= data.get("total", 0):
                break
            page += 1
        print("[ok] Test Case %d건 조회 (이름 기준 매칭 대상)" % len(mapping))
        return mapping

    def fetch_schema(self, tracker_id):
        """트래커 스키마를 읽어 필드명과 선택지 옵션을 확보한다."""
        resp = self.s.get(self._url("/trackers/%s/schema" % tracker_id), timeout=TIMEOUT)
        raw = self._check(resp, "트래커 스키마 조회")
        fields = raw if isinstance(raw, list) else raw.get("fields", raw)
        out = {}
        for f in fields if isinstance(fields, list) else []:
            key = f.get("legacyRestName") or f.get("name")
            out[key] = {
                "name": f.get("name"),
                "type": f.get("type"),
                "options": [o.get("name") for o in f.get("options", [])],
                "mandatory": bool(f.get("mandatoryInStatuses")),
            }
        return out

    def check_schema(self, tracker_id):
        """전송 전 프리플라이트.

        보낼 값이 실제 트래커의 선택지에 존재하는지 미리 확인한다.
        이 검사가 없어서 Passed 를 Status 에 보내는 오류를 오래 못 잡았다.
        다국어 인스턴스는 옵션 이름이 로컬라이즈되므로 특히 필요하다.
        """
        schema = self.fetch_schema(tracker_id)
        print("[ok] 트래커 %s 스키마 필드 %d개" % (tracker_id, len(schema)))

        problems = []
        for field_key, wanted in (("result", [RESULT_PASSED, RESULT_FAILED, RESULT_BLOCKED]),
                                  ("status", [RUN_STATUS_DONE])):
            info = schema.get(field_key)
            if not info:
                problems.append("필드 '%s' 가 트래커에 없다" % field_key)
                continue
            opts = info["options"]
            print("  %-8s (%s) 옵션: %s" % (field_key, info["name"], ", ".join(opts) or "-"))
            for w in wanted:
                if opts and w not in opts:
                    problems.append("'%s' 는 %s 필드의 유효한 옵션이 아니다 (가능: %s)"
                                    % (w, field_key, ", ".join(opts)))

        for key in ("build", "testCases"):
            info = schema.get(key)
            if info:
                print("  %-8s (%s) type=%s mandatory=%s"
                      % (key, info["name"], info["type"], info["mandatory"]))
            else:
                problems.append("필드 '%s' 가 트래커에 없다" % key)

        tc = schema.get("testCases")
        if tc and tc["mandatory"]:
            print("  [주의] testCases 는 필수 필드다. Test Case 매칭 없이는 생성이 거부된다.")

        if problems:
            sys.stderr.write("\n[스키마 불일치]\n")
            for p_ in problems:
                sys.stderr.write("  - %s\n" % p_)
            return False
        print("[ok] 스키마 프리플라이트 통과")
        return True

    def post_automated_test_runs(self, tracker_id, run_name, suite, case_ids,
                                 description, build_ref=""):
        """
        POST /api/v3/trackers/{testRunTrackerId}/automatedtestruns

        필드 매핑은 실측 스키마(Automotive Template 3.0, tracker 123469) 기준이다.
          status     워크플로 상태  -> "Finished"
          result     시험 결과      -> Passed / Failed / Blocked
          build      빌드 식별자    -> 전용 TextField (description 에 넣지 않는다)
          testCases  Test Case 표   -> 필수. testCase 참조 + 개별 result

        Passed/Failed 를 status 에 보내던 것이 원래 오류였다.
        Status 옵션에는 Passed 가 없다 (Unset/In progress/.../Finished/Closed 등).
        """
        rows = []
        unmatched = []
        for r in suite.results:
            cid = case_ids.get(r.name)
            if cid is None:
                unmatched.append(r.name)
                continue
            rows.append({
                "testCase": {"id": cid, "type": "TrackerItemReference"},
                "active": True,
                "result": r.status,
            })

        if unmatched:
            print("[warn] Test Case 미매칭 %d건 (Test Case 트래커에 동명 항목 없음):"
                  % len(unmatched))
            for n in unmatched[:5]:
                print("         - %s" % n)
            if len(unmatched) > 5:
                print("         ... 외 %d건" % (len(unmatched) - 5))

        payload = {
            "name": run_name,
            "description": description,
            "descriptionFormat": "Html",
            "status": RUN_STATUS_DONE,
            "result": suite.overall_result,
            "testCases": rows,
        }
        if build_ref:
            payload["build"] = build_ref

        if self.dry_run:
            print("[dry-run] POST /trackers/%s/automatedtestruns" % tracker_id)
            print(json.dumps(payload, indent=2, ensure_ascii=False)[:3000])
            return {"id": -1}

        if not rows:
            sys.stderr.write(
                "[FAIL] 연결할 Test Case 가 하나도 없다. testCases 는 필수 필드이므로\n"
                "       이대로 전송하면 거부된다. CB_TEST_CASE_TRACKER_ID 를 설정하고\n"
                "       Test Case 항목명을 자동화 테스트 함수명과 일치시키십시오.\n")
            raise requests.HTTPError("testCases empty")

        resp = self.s.post(self._url("/trackers/%s/automatedtestruns" % tracker_id),
                           json=payload, timeout=TIMEOUT)
        data = self._check(resp, "자동화 Test Run 생성 (%s)" % run_name)
        run_id = data.get("id") or (data.get("items") or [{}])[0].get("id")
        print("[ok] Test Run 생성: id=%s result=%s (Test Case %d건 연결)"
              % (run_id, suite.overall_result, len(rows)))
        return data

    def attach(self, item_id, file_path, description=""):
        """POST /api/v3/items/{itemId}/attachments — 커버리지 리포트 등 증적 첨부."""
        if not os.path.exists(file_path):
            print("[skip] 첨부 대상 없음: %s" % file_path)
            return
        if self.dry_run or not item_id or item_id < 0:
            print("[dry-run] attach %s -> item %s" % (file_path, item_id))
            return
        with open(file_path, "rb") as fh:
            resp = self.s.post(
                self._url("/items/%s/attachments" % item_id),
                files={"attachments": (os.path.basename(file_path), fh, "application/xml")},
                data={"description": description},
                timeout=TIMEOUT,
            )
        self._check(resp, "첨부 업로드 (%s)" % file_path)
        print("[ok] 첨부 완료: %s -> item %s" % (os.path.basename(file_path), item_id))


# --------------------------------------------------------------------------- #
def build_description(build_ref, commit, cov):
    # build 는 전용 필드로 따로 보내지만, 사람이 읽는 설명에도 남겨 둔다
    rows = ["<p><b>Build:</b> %s<br/><b>Commit:</b> %s</p>"
            % (build_ref or "-", commit or "-")]
    if cov:
        rows.append("<p><b>Code Coverage</b><br/>Line: %s%%<br/>Branch: %s%%</p>"
                    % (cov["line"], cov["branch"]))
    return "".join(rows)


def main():
    ap = argparse.ArgumentParser(description="CI 결과를 Codebeamer 로 전송")
    ap.add_argument("--unit-report", help="단위 시험 JUnit XML")
    ap.add_argument("--func-report", help="기능 시험 JUnit XML")
    ap.add_argument("--coverage", help="gcovr Cobertura XML")
    ap.add_argument("--build-ref", default="", help="빌드 식별자")
    ap.add_argument("--commit", default="", help="커밋 SHA")
    ap.add_argument("--dry-run", action="store_true",
                    help="전송하지 않고 페이로드만 출력 (스키마 대조용)")
    ap.add_argument("--check-schema", action="store_true",
                    help="트래커 스키마를 조회해 보낼 값이 유효한지만 확인하고 종료")
    args = ap.parse_args()

    base_url = os.environ.get("CB_URL")
    tracker_id = os.environ.get("CB_TEST_RUN_TRACKER_ID")
    if not args.dry_run and (not base_url or not tracker_id):
        sys.stderr.write("CB_URL / CB_TEST_RUN_TRACKER_ID 환경변수가 필요합니다.\n")
        return 2

    # 스키마 프리플라이트만 수행하고 종료
    if args.check_schema:
        client = CodebeamerClient(base_url, os.environ.get("CB_TOKEN"),
                                  os.environ.get("CB_USER"), os.environ.get("CB_PASS"))
        return 0 if client.check_schema(tracker_id) else 1

    cov = parse_coverage(args.coverage)
    description = build_description(args.build_ref, args.commit, cov)

    suites = [s for s in (parse_junit(args.unit_report, "Automated Unit Test Run"),
                          parse_junit(args.func_report, "Automated Functional Test Run"))
              if s is not None]
    if not suites:
        sys.stderr.write("전송할 테스트 결과가 없습니다.\n")
        return 1

    client = CodebeamerClient(
        base_url or "http://localhost/cb",
        os.environ.get("CB_TOKEN"),
        os.environ.get("CB_USER"),
        os.environ.get("CB_PASS"),
        dry_run=args.dry_run,
    )
    case_ids = {} if args.dry_run else client.find_test_case_ids(
        os.environ.get("CB_TEST_CASE_TRACKER_ID", "")
    )

    exit_code = 0
    for suite in suites:
        run_name = "%s - %s" % (suite.label, args.build_ref or "local")
        try:
            data = client.post_automated_test_runs(
                tracker_id or "0", run_name, suite, case_ids, description,
                build_ref=args.build_ref)
        except requests.HTTPError:
            exit_code = 1
            continue

        run_id = data.get("id")
        # 커버리지 증적은 단위 시험 Run 에 1회만 첨부
        if args.coverage and suite.label.startswith("Automated Unit") and run_id:
            try:
                client.attach(run_id, args.coverage, "gcovr Cobertura coverage report")
            except requests.HTTPError:
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
