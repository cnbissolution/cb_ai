#!/usr/bin/env python3
"""
데모용 Codebeamer 프로젝트 채우기 — SRS 부터 Test Case 까지

이 저장소의 산출물을 실제 Codebeamer 프로젝트에 올린다.
  docs/SRS_AEB_Requirements.csv  -> Requirements 트래커 (계층 구조 + ASIL)
  req_index.json (@verifies)     -> Test Cases 트래커 (이름 = 테스트 함수명)
  GitHub Pages req/<ID>/         -> 각 항목 설명의 코드 링크

Test Case 항목명을 자동화 테스트 함수명과 **정확히 일치**시키는 것이 핵심이다.
upload_to_codebeamer.py 가 이름으로 매칭해 Test Run 을 연결하기 때문이다.

사용:
  # 1) 무엇이 생성될지 먼저 확인 (기본값, 서버에 아무것도 안 씀)
  python3 scripts/seed_codebeamer_demo.py --project-id 123

  # 2) 트래커까지 새로 만들면서 실제 생성
  python3 scripts/seed_codebeamer_demo.py --project-id 123 --create-trackers --apply

  # 3) 이미 있는 트래커(예: Automotive Template 로 만든 프로젝트)에 채우기
  python3 scripts/seed_codebeamer_demo.py --project-id 123 \
      --req-tracker 123545 --tc-tracker 123478 --apply

환경변수:
  CB_URL, CB_TOKEN (또는 CB_USER/CB_PASS)

주의: --apply 는 서버에 실제로 항목을 생성한다. 되돌리려면 수동 삭제해야 한다.
      반드시 dry-run 으로 먼저 확인할 것.
      프로젝트 생성 API 는 v3 에 없으므로 대상 프로젝트는 UI 에서 먼저 만든다.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 30

PAGES_BASE = os.environ.get("PAGES_BASE", "https://cnbissolution.github.io/cb_ai")

# GET /v3/trackers/types 로 확인한 값
TRACKER_TYPES = {
    "requirement": 5,
    "testcase": 102,
    "testrun": 9,
    "bug": 2,
}

TRACKERS_TO_CREATE = [
    ("AEB Software Requirements", "requirement",
     "SWE.1 소프트웨어 요구사항 (AEB 센서 퓨전 엔진)"),
    ("AEB Test Cases", "testcase",
     "SWE.4 검증 - 자동화 테스트 케이스. 항목명은 테스트 함수명과 일치시킨다"),
    ("AEB Test Runs", "testrun",
     "CI 파이프라인이 automatedtestruns API 로 생성하는 실행 기록"),
    ("AEB Bugs", "bug",
     "AI 에이전트가 실패 분석 결과를 코멘트로 남기는 결함 항목"),
]


# --------------------------------------------------------------------------- #
class CB:
    def __init__(self, base_url, token, user, password, apply=False):
        self.base = base_url.rstrip("/")
        self.apply = apply
        self.s = requests.Session()
        if token:
            self.s.headers["Authorization"] = "Bearer %s" % token
        elif user and password:
            self.s.auth = (user, password)
        elif apply:
            raise SystemExit("인증 정보 없음: CB_TOKEN 또는 CB_USER/CB_PASS 를 설정하십시오.")
        self.s.headers["Accept"] = "application/json"
        retry = Retry(total=3, backoff_factor=1.0,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET", "POST", "PUT"])
        self.s.mount("https://", HTTPAdapter(max_retries=retry))
        self.s.mount("http://", HTTPAdapter(max_retries=retry))
        self._fake_id = -1

    def _url(self, path):
        return "%s/api/v3%s" % (self.base, path)

    def _check(self, resp, what):
        if not resp.ok:
            sys.stderr.write("[FAIL] %s: HTTP %d\n%s\n"
                             % (what, resp.status_code, resp.text[:800]))
            resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return {}

    def _next_fake(self):
        self._fake_id -= 1
        return self._fake_id

    # --- 조회 --------------------------------------------------------------
    def list_trackers(self, project_id):
        resp = self.s.get(self._url("/projects/%s/trackers" % project_id), timeout=TIMEOUT)
        data = self._check(resp, "트래커 목록 조회")
        items = data if isinstance(data, list) else data.get("items", [])
        return {t.get("name"): t.get("id") for t in items}

    # --- 생성 --------------------------------------------------------------
    def create_tracker(self, project_id, name, type_key, description):
        payload = {
            "name": name,
            "description": description,
            "type": {"id": TRACKER_TYPES[type_key], "type": "TrackerTypeReference"},
        }
        if not self.apply:
            print("    [dry-run] 트래커 생성: %s (type=%s)" % (name, type_key))
            return self._next_fake()
        resp = self.s.post(self._url("/projects/%s/trackers" % project_id),
                           json=payload, timeout=TIMEOUT)
        data = self._check(resp, "트래커 생성 (%s)" % name)
        tid = data.get("id")
        print("    [ok] 트래커 생성: %s -> id=%s" % (name, tid))
        return tid

    def create_item(self, tracker_id, name, description, parent_id=None):
        payload = {
            "name": name,
            "description": description,
            "descriptionFormat": "Html",
        }
        if not self.apply:
            return self._next_fake()
        if parent_id and parent_id > 0:
            url = self._url("/items/%s/children" % parent_id)
        else:
            url = self._url("/trackers/%s/items" % tracker_id)
        resp = self.s.post(url, json=payload, timeout=TIMEOUT)
        data = self._check(resp, "항목 생성 (%s)" % name[:40])
        return data.get("id")


# --------------------------------------------------------------------------- #
def load_srs():
    """SRS CSV 를 읽어 헤딩/요구사항으로 분리한다."""
    path = ROOT / "docs" / "SRS_AEB_Requirements.csv"
    if not path.exists():
        raise SystemExit("SRS CSV 가 없습니다: %s" % path)
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if not (r.get("Req ID") or "").strip():
                continue
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def load_req_index():
    """req_index.json 의 @verifies 에서 테스트 케이스 목록을 만든다."""
    path = ROOT / "req_index.json"
    if not path.exists():
        print("[warn] req_index.json 이 없습니다. 먼저 build_symbol_map.py 를 실행하십시오.")
        return {}
    req = json.loads(path.read_text(encoding="utf-8"))
    cases = {}
    for rid, entries in req.items():
        for e in entries:
            if e["kind"] != "verifies":
                continue
            c = cases.setdefault(e["symbol"], {"file": e["file"], "reqs": [], "url": e["url"]})
            if rid not in c["reqs"]:
                c["reqs"].append(rid)
    return cases


def req_description(row):
    rid = row["Req ID"]
    parts = ["<p>%s</p>" % row.get("Requirement Text", "")]
    meta = []
    for label, key in (("Type", "Type"), ("ASIL", "ASIL"),
                       ("Verification", "Verification Method"), ("Status", "Status")):
        if row.get(key):
            meta.append("<b>%s:</b> %s" % (label, row[key]))
    if meta:
        parts.append("<p>%s</p>" % " &middot; ".join(meta))
    if rid.startswith("SRS-"):
        link = "%s/req/%s/" % (PAGES_BASE, rid)
        parts.append('<p><b>Code Link:</b> <a href="%s">%s</a><br/>'
                     '<i>심볼 기준 안정 링크. 라인 번호가 바뀌어도 유효하다.</i></p>'
                     % (link, link))
    return "".join(parts)


def case_description(name, info):
    reqs = ", ".join(info["reqs"])
    links = " ".join('<a href="%s/req/%s/">%s</a>' % (PAGES_BASE, r, r) for r in info["reqs"])
    return ("<p>자동화 테스트 케이스. 항목명이 테스트 함수명과 일치해야 "
            "CI 가 Test Run 을 자동 연결한다.</p>"
            "<p><b>소스:</b> <code>%s</code><br/>"
            "<b>검증 요구사항:</b> %s</p>"
            "<p><b>코드:</b> <a href=\"%s\">GitHub</a><br/>"
            "<b>요구사항 링크:</b> %s</p>"
            % (info["file"], reqs, info["url"], links))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="데모용 Codebeamer 프로젝트 채우기")
    ap.add_argument("--project-id", type=int, required=True, help="대상 프로젝트 ID")
    ap.add_argument("--create-trackers", action="store_true",
                    help="트래커 4종을 새로 만든다 (없을 때만)")
    ap.add_argument("--req-tracker", type=int, help="기존 Requirements 트래커 ID")
    ap.add_argument("--tc-tracker", type=int, help="기존 Test Case 트래커 ID")
    ap.add_argument("--apply", action="store_true",
                    help="실제로 서버에 생성한다 (미지정 시 dry-run)")
    args = ap.parse_args()

    base_url = os.environ.get("CB_URL")
    if args.apply and not base_url:
        sys.stderr.write("CB_URL 환경변수가 필요합니다.\n")
        return 2

    cb = CB(base_url or "http://localhost/cb", os.environ.get("CB_TOKEN"),
            os.environ.get("CB_USER"), os.environ.get("CB_PASS"), apply=args.apply)

    mode = "실제 생성 (--apply)" if args.apply else "DRY-RUN (서버에 쓰지 않음)"
    print("=" * 74)
    print(" 대상 프로젝트: %s   모드: %s" % (args.project_id, mode))
    print("=" * 74)

    # ---- 1. 트래커 확보 ----
    print("\n[1] 트래커")
    existing = {}
    if args.apply or args.create_trackers:
        try:
            existing = cb.list_trackers(args.project_id)
            print("    기존 트래커 %d개" % len(existing))
        except requests.HTTPError:
            return 1

    tracker_ids = {}
    if args.create_trackers:
        for name, type_key, desc in TRACKERS_TO_CREATE:
            if name in existing:
                tracker_ids[type_key] = existing[name]
                print("    [skip] 이미 있음: %s (id=%s)" % (name, existing[name]))
            else:
                tracker_ids[type_key] = cb.create_tracker(
                    args.project_id, name, type_key, desc)
    else:
        tracker_ids["requirement"] = args.req_tracker
        tracker_ids["testcase"] = args.tc_tracker
        if not (args.req_tracker and args.tc_tracker):
            print("    [info] --req-tracker / --tc-tracker 미지정.")
            print("           --create-trackers 를 쓰거나 기존 트래커 ID 를 지정하십시오.")
            if args.apply:
                return 2
            tracker_ids["requirement"] = tracker_ids["requirement"] or -900
            tracker_ids["testcase"] = tracker_ids["testcase"] or -901

    # ---- 2. 요구사항 ----
    print("\n[2] 요구사항 (docs/SRS_AEB_Requirements.csv)")
    rows = load_srs()
    heading_ids = {}
    created_reqs = {}
    n_head = n_req = 0

    for row in rows:
        rid = row["Req ID"]
        if row.get("Type") == "Heading":
            item_id = cb.create_item(tracker_ids["requirement"], "%s %s"
                                     % (rid, row.get("Requirement Text", "")),
                                     req_description(row))
            heading_ids[rid] = item_id
            n_head += 1
            print("    + [헤딩]   %s" % rid)

    for row in rows:
        rid = row["Req ID"]
        if row.get("Type") == "Heading":
            continue
        text = row.get("Requirement Text", "")
        parent = heading_ids.get(row.get("Parent ID", ""))
        item_id = cb.create_item(tracker_ids["requirement"],
                                 "%s %s" % (rid, text[:60]),
                                 req_description(row), parent_id=parent)
        created_reqs[rid] = item_id
        n_req += 1
        flag = ""
        if row.get("Status", "").startswith("Proposed"):
            flag = "  (제안 - 미승인)"
        elif "Hold" in row.get("Status", ""):
            flag = "  (보류 - 도달불가)"
        print("    + %-14s %-6s %s%s" % (rid, row.get("ASIL", "-"), text[:44], flag))

    # ---- 3. 테스트 케이스 ----
    print("\n[3] 테스트 케이스 (req_index.json 의 @verifies)")
    cases = load_req_index()
    n_case = 0
    for name in sorted(cases):
        info = cases[name]
        cb.create_item(tracker_ids["testcase"], name, case_description(name, info))
        n_case += 1
        print("    + %-56s <- %s" % (name[:56], ", ".join(info["reqs"])))

    # ---- 요약 ----
    print("\n" + "=" * 74)
    print(" 요약: 헤딩 %d / 요구사항 %d / 테스트케이스 %d" % (n_head, n_req, n_case))
    if not args.apply:
        print(" DRY-RUN 이었다. 실제로 생성하려면 --apply 를 붙일 것.")
    else:
        print(" 생성 완료. 아래 값을 GitHub Secrets 에 등록하십시오:")
        print("   CB_TEST_RUN_TRACKER_ID  = %s" % tracker_ids.get("testrun", "(확인 필요)"))
        print("   CB_TEST_CASE_TRACKER_ID = %s" % tracker_ids.get("testcase"))
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
