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
                            CB_API_TOKEN 이름도 받는다
  CB_USER / CB_PASS         Basic 인증 (CB_TOKEN 미설정 시 대체)
                            CB_USERNAME / CB_PASSWORD 이름도 받는다
  CB_TEST_RUN_TRACKER_ID    Test Run 트래커 ID
  CB_TEST_CASE_TRACKER_ID   Test Case 트래커 ID. **쉼표로 여러 개** 가능
                            (단위시험 SWE.4 와 소프트웨어 검증 SWE.6 이
                             서로 다른 트래커에 있다)

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cb_common      # noqa: E402

TIMEOUT = 30

# Test Case 의 `GTest Name` 필드 id. 이 필드에 `Suite.Case` 를 쉼표로
# 나열해 두면 제목을 고쳐도 매칭이 끊기지 않는다. 0 이면 이름으로만 맞춘다.
GTEST_FIELD_ID = int(os.environ.get("CB_GTEST_FIELD_ID", "10005") or 0)

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
        # 자격증명 해석은 cb_common 에 맡긴다. 환경변수 이름이 두 갈래
        # (CB_URL/CB_TOKEN 과 CB_BASE_URL/CB_API_TOKEN) 라 여기서 한쪽만
        # 보면 다른 설정에서 401 이 난다.
        self.base = cb_common.base_url(base_url)
        self.dry_run = dry_run
        try:
            self.s = cb_common.session()
        except SystemExit:
            if not dry_run:
                raise
            self.s = requests.Session()

        self.s.headers["Accept"] = "application/json"
        retry = Retry(total=3, backoff_factor=1.0,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET", "POST", "PUT"])
        self.s.mount("https://", HTTPAdapter(max_retries=retry))
        self.s.mount("http://", HTTPAdapter(max_retries=retry))

    def _url(self, path):
        return "%s/api/v3%s" % (self.base, path)

    def _check(self, resp, what):
        """상태코드를 반드시 확인한다. 원본 결함(D-5): 확인 없이 json()['id'] 에
        접근하여 실패 시 KeyError 로 엉뚱한 지점에서 파이프라인이 죽었다."""
        if not resp.ok:
            sys.stderr.write("[FAIL] %s: HTTP %d\n" % (what, resp.status_code))
            sys.stderr.write("        %s\n" % resp.text[:1000])
            resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return {}

    def find_test_case_ids(self, tracker_ids):
        """Test Case 의 **매칭 키 -> ID** 매핑을 조회한다
        (ASPICE 4.0 SWE.4.BP4 — 검증 결과 <-> 검증 방안).

        매칭 키는 두 갈래로 모은다.

          1. `GTest Name` 필드 (권장) — `Suite.Case` 를 쉼표로 나열한다
          2. 항목 이름 (되돌아갈 길) — 필드가 비어 있는 옛 항목을 위해 남긴다

        **필드를 정본으로 삼는 이유.** 제목으로 맞추면 한글 제목을 다듬는
        순간 매칭이 끊기는데, 끊겼다는 걸 아무도 모른다. 실제로 이 프로젝트에서
        시험 결과와 케이스 연결이 한 번도 성사된 적이 없었고 화면상으로는
        정상이었다. 필드는 사람이 읽는 값이 아니라 기계의 키라 안 건드린다.

        한 명세가 여러 케이스를 갖는 경우(경계값 시험)도 쉼표로 담긴다.

        `tracker_ids` 는 쉼표로 구분된 여러 개를 받는다. 단위시험(SWE.4)과
        소프트웨어 검증(SWE.6)이 서로 다른 트래커에 있기 때문이다.
        """
        raw = str(tracker_ids or "").strip()
        if not raw:
            print("[info] CB_TEST_CASE_TRACKER_ID 미설정 - Test Case 링크 생략")
            return {}

        mapping = {}
        for tid in [x.strip() for x in raw.split(",") if x.strip()]:
            page, got, keyed = 1, 0, 0
            while True:
                resp = self.s.get(self._url("/trackers/%s/items" % tid),
                                  params={"page": page, "pageSize": 100},
                                  timeout=TIMEOUT)
                data = self._check(resp, "Test Case 목록 조회 (%s)" % tid)
                # 이 엔드포인트는 `itemRefs` 로 준다. `items` 로 읽으면
                # 항상 0건이 되어 매칭이 조용히 실패한다
                items = data.get("itemRefs") or data.get("items") or []
                if not items:
                    break
                for it in items:
                    entry = {"id": it["id"], "name": it.get("name") or "",
                             "tracker": int(tid)}
                    if it.get("name"):
                        mapping.setdefault(it["name"], entry)
                    for key in self._gtest_keys(it["id"]):
                        mapping[key] = entry             # 필드가 이름을 이긴다
                        keyed += 1
                got += len(items)
                if page * 100 >= data.get("total", 0):
                    break
                page += 1
            print("[ok] 트래커 %s: Test Case %d건 (GTest Name %d개)"
                  % (tid, got, keyed))

        print("[ok] 매칭 키 %d개 확보" % len(mapping))
        return mapping

    def _gtest_keys(self, item_id):
        """항목의 `GTest Name` 필드에서 매칭 키를 꺼낸다. 없으면 빈 목록.

        필드가 비어 있으면 그 Test Case 는 **자동화되지 않은 것**이다. 수동
        시험이 섞인 프로젝트에서 이 구분이 중요하므로 조용히 이름으로
        떨어지되, 위 호출부가 개수를 찍어 눈에 보이게 한다.
        """
        if not GTEST_FIELD_ID:
            return []
        try:
            resp = self.s.get(self._url("/items/%s" % item_id), timeout=TIMEOUT)
            data = self._check(resp, "Test Case 조회 (%s)" % item_id)
        except Exception:                                 # noqa: BLE001
            return []
        raw = next((f.get("value") for f in data.get("customFields") or []
                    if f.get("fieldId") == GTEST_FIELD_ID), "") or ""
        return [k.strip() for k in raw.split(",") if k.strip()]

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
        """Test Run 을 만들고 케이스별 결과를 채운다. **두 번 부른다.**

            1. POST /v3/trackers/{runTracker}/testruns
                 `testCaseIds` 로 실행을 만든다. 부모 Run 1개 + 케이스별 자식
                 Run 이 생기고, 시험 절차(Test Step)가 명세에서 복사돼 온다
            2. PUT  /v3/testruns/{parentId}
                 `updateRequestModels` 로 케이스별 PASSED/FAILED 를 넣는다.
                 `parentResultPropagation` 이 부모 결과까지 굴려 올린다

        **`automatedtestruns` 를 쓰지 않는 이유.** 그쪽은 Test Case 를
        `groupName`(폴더) + `name` 으로 **이름 매칭**한다. 즉 ALM 의 폴더
        구조를 GTest 픽스처 이름에 맞춰 두어야 하고, 제목을 고치면 조용히
        끊긴다. 여기 쓰는 경로는 **항목 id 로 붙으므로** 우리 매칭 키
        (`GTest Name` 필드)의 값어치가 그대로 유지된다.

        스펙 근거는 `/api-docs` 의 CreateTestRunRequest / UpdateTestRunRequest.
        결과 enum 은 **대문자**다 — PASSED / FAILED / BLOCKED / NOT_APPLICABLE.
        """
        ENUM = {RESULT_PASSED: "PASSED", RESULT_FAILED: "FAILED",
                RESULT_BLOCKED: "BLOCKED"}

        seen, updates, unmatched = [], [], []
        for r in suite.results:
            # `Suite.Case` 를 먼저 본다. JUnit 의 classname 이 GTest 픽스처
            # (pytest 는 모듈 경로)라 가장 구체적인 키다. 못 찾으면 케이스
            # 이름만으로 물러선다 — GTest Name 을 아직 안 채운 항목을 위해서다.
            hit = None
            for key in ((("%s.%s" % (r.classname, r.name)) if r.classname else None),
                        r.name):
                if key and key in case_ids:
                    hit = case_ids[key]
                    break
            if hit is None:
                unmatched.append(("%s.%s" % (r.classname, r.name))
                                 if r.classname else r.name)
                continue
            if hit["id"] not in seen:
                seen.append(hit["id"])
            row = {"testCaseReference": {"id": hit["id"],
                                         "type": "TrackerItemReference"},
                   "result": ENUM.get(r.status, "BLOCKED")}
            if r.duration_ms:
                row["runTime"] = max(1, r.duration_ms // 1000)
            if r.message:
                row["conclusion"] = r.message[:900]
            updates.append(row)

        if unmatched:
            print("[warn] Test Case 미매칭 %d건 — `GTest Name` 필드나 항목명을 "
                  "확인하십시오:" % len(unmatched))
            for n in unmatched[:5]:
                print("         - %s" % n)
            if len(unmatched) > 5:
                print("         ... 외 %d건" % (len(unmatched) - 5))

        create = {"testCaseIds": seen,
                  "testRunModel": {"name": run_name,
                                   "description": description,
                                   "descriptionFormat": "Wiki"}}

        if self.dry_run:
            print("[dry-run] POST /trackers/%s/testruns" % tracker_id)
            print(json.dumps(create, indent=2, ensure_ascii=False)[:1500])
            print("[dry-run] PUT /testruns/{id}  결과 %d건" % len(updates))
            print(json.dumps(updates[:3], indent=2, ensure_ascii=False)[:900])
            return {"id": -1}

        if not seen:
            sys.stderr.write(
                "[FAIL] 연결할 Test Case 가 하나도 없다. 결과만 올리면 "
                "무엇을 검증한 것인지 알 수 없어 증적이 되지 않는다.\n"
                "       CB_TEST_CASE_TRACKER_ID 를 설정하고 Test Case 의 "
                "`GTest Name` 필드를 채우십시오.\n")
            raise requests.HTTPError("no matching test case")

        resp = self.s.post(self._url("/trackers/%s/testruns" % tracker_id),
                           json=create, timeout=TIMEOUT)
        data = self._check(resp, "Test Run 생성 (%s)" % run_name)
        run_id = data.get("id")

        resp = self.s.put(self._url("/testruns/%s" % run_id),
                          json={"parentResultPropagation": True,
                                "updateRequestModels": updates},
                          timeout=TIMEOUT)
        self._check(resp, "Test Run 결과 반영 (%s)" % run_id)

        print("[ok] Test Run %s — 케이스 %d건 (%s)"
              % (run_id, len(updates), suite.overall_result))
        return data
    def attach(self, item_id, file_path, description=""):
        """POST /api/v3/items/{itemId}/attachments — 커버리지 리포트 등 증적 첨부.
        원본 결함(D-5): 커버리지 파일을 인자로만 받고 업로드하지 않았다."""
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
    """Test Run 설명. 위키 마크업으로 만든다 — Codebeamer 는 Html 을 거부한다
    (400 Description format 'HTML' is deprecated)."""
    # build 는 전용 필드로 따로 보내지만, 사람이 읽는 설명에도 남겨 둔다
    rows = ["||항목||값",
            "|__Build__|%s" % (build_ref or "-"),
            "|__Commit__|%s" % (commit or "-")]
    if cov:
        rows.append("|__Line Coverage__|%s%%" % cov["line"])
        rows.append("|__Branch Coverage__|%s%%" % cov["branch"])
    return "\n".join(rows)


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

    # cb_common 이 CB_URL / CB_BASE_URL 둘 다 본다. 여기서 한쪽만 읽어
    # 넘기면 다른 이름으로 설정한 환경에서 기본값이 우선해버린다
    base_url = os.environ.get("CB_URL") or os.environ.get("CB_BASE_URL")
    # ASPICE 는 BP 별로 산출물을 요구한다. 단위 검증(SWE.4) 결과와 소프트웨어
    # 검증(SWE.6) 결과를 한 트래커에 섞으면 심사에서 갈라 보여줄 수 없다.
    # 레벨별 트래커가 없으면 예전처럼 한 곳으로 떨어진다.
    fallback = os.environ.get("CB_TEST_RUN_TRACKER_ID")
    run_trackers = {
        "Automated Unit Test Run":
            os.environ.get("CB_UNIT_RUN_TRACKER_ID") or fallback,
        "Automated Functional Test Run":
            os.environ.get("CB_VERIF_RUN_TRACKER_ID") or fallback,
    }
    tracker_id = fallback or next((v for v in run_trackers.values() if v), None)
    if not args.dry_run and (not base_url or not any(run_trackers.values())):
        sys.stderr.write(
            "CB_URL 과 결과 트래커가 필요합니다 — CB_UNIT_RUN_TRACKER_ID / "
            "CB_VERIF_RUN_TRACKER_ID (또는 CB_TEST_RUN_TRACKER_ID).\n")
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
        base_url,
        os.environ.get("CB_TOKEN"),
        os.environ.get("CB_USER"),
        os.environ.get("CB_PASS"),
        dry_run=args.dry_run,
    )
    # 조회는 GET 이라 서버에 영향이 없다. dry-run 에서도 돌려야
    # 이름 매칭이 실제로 되는지 미리 확인할 수 있다
    case_ids = client.find_test_case_ids(
        os.environ.get("CB_TEST_CASE_TRACKER_ID", "")
    )

    exit_code = 0
    for suite in suites:
        run_name = "%s - %s" % (suite.label, args.build_ref or "local")
        try:
            target = run_trackers.get(suite.label) or tracker_id or "0"
            data = client.post_automated_test_runs(
                target, run_name, suite, case_ids, description,
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
