#!/usr/bin/env python3
"""Codebeamer Task 에서 CT(시험) 파이프라인을 실행하고 결과를 그 Task 로 되돌린다.

데모 시현용 왕복 경로다.

  Codebeamer Task ──(1)──> GitHub repository_dispatch
                              │
                              ├─ gtest / pytest 실행
                              └─ upload_to_codebeamer.py 가 Test Run 생성
                                    │
  Codebeamer Task <──(2)────────────┘   결과를 댓글·상태로 되돌린다

왜 브리지가 필요한가
  Codebeamer 쪽에서 밖으로 HTTP 를 쏘려면 트래커 워크플로 액션이나 웹훅 설정이
  필요한데, 이 서버는 REST v3 에 웹훅 경로가 없고(스펙 확인) 관리 화면에서만
  만질 수 있다. 그래서 **Codebeamer 를 지켜보다 대신 쏘는** 얇은 브리지를 둔다.
  Codebeamer 를 고치지 않으므로 데모 후 되돌릴 것도 없다.

두 가지 모드

  한 번 실행 (검증·리허설용)
    python scripts/cb_run_ct.py --task <Task 항목 id>

  지켜보기 (시현 중 계속 띄워 둔다)
    python scripts/cb_run_ct.py --watch
      TASK 트래커에서 제목이 `CT-RUN` 으로 시작하고 상태가 감시 상태인 항목을 찾아
      실행한다. 발표자는 Codebeamer 화면에서 **상태만 바꾸면** 된다.

환경변수
  CB_URL / CB_BASE_URL          코드비머 주소
  CB_TOKEN / CB_USER+CB_PASS    인증 (cb_common 과 같은 규칙)
  GITHUB_PERSONAL_ACCESS_TOKEN  repository_dispatch 를 쏠 토큰
  GITHUB_REPOSITORY             owner/repo (기본 인자로도 받는다)

트래커·항목 id 는 인자나 환경변수로만 받는다. 이 저장소는 공개다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cb_common import TIMEOUT, base_url, check, session, tracker_id  # noqa: E402

GH_API = "https://api.github.com"
WATCH_PREFIX = "CT-RUN"


# ── GitHub ────────────────────────────────────────────────────────────────────
def gh(method: str, path: str, body=None):
    tok = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get("GITHUB_PAT")
    if not tok:
        raise SystemExit("GITHUB_PERSONAL_ACCESS_TOKEN 이 필요하다.")
    r = urllib.request.Request(
        GH_API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + tok,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp:
        raw = resp.read()
        return resp.status, (json.loads(raw) if raw else None)


def fire(repo: str, task_id: int) -> set:
    """dispatch 를 쏘기 **전에** 기존 run id 를 찍어 둔다.

    dispatch 응답에는 run id 가 없다. 새로 생긴 것을 찾는 수밖에 없어서,
    쏘기 전 목록과 비교한다."""
    _, d = gh("GET", "/repos/%s/actions/runs?per_page=20" % repo)
    before = {x["id"] for x in d.get("workflow_runs", [])}
    s, _ = gh("POST", "/repos/%s/dispatches" % repo,
              {"event_type": "codebeamer-test-request",
               "client_payload": {"cb_item_id": str(task_id)}})
    if s != 204:
        raise SystemExit("dispatch 실패: HTTP %s" % s)
    return before


def wait_run(repo: str, before: set, minutes: int = 12) -> dict:
    run = None
    for _ in range(int(minutes * 60 / 5)):
        time.sleep(5)
        _, d = gh("GET", "/repos/%s/actions/runs?per_page=20" % repo)
        new = [x for x in d.get("workflow_runs", [])
               if x["id"] not in before and (x.get("name") or "").startswith("AEB")]
        if new:
            run = new[0]
            break
    if not run:
        raise SystemExit("새 워크플로 실행을 찾지 못했다.")
    for _ in range(int(minutes * 60 / 10)):
        _, d = gh("GET", "/repos/%s/actions/runs/%s" % (repo, run["id"]))
        if d.get("status") == "completed":
            return d
        time.sleep(10)
    raise SystemExit("실행이 %d분 안에 끝나지 않았다 (run %s)." % (minutes, run["id"]))


def step_results(repo: str, run_id: int) -> list:
    _, d = gh("GET", "/repos/%s/actions/runs/%s/jobs" % (repo, run_id))
    out = []
    for j in d.get("jobs", []):
        for s in j.get("steps", []):
            out.append((s.get("name"), s.get("conclusion")))
    return out


# ── Codebeamer ────────────────────────────────────────────────────────────────
def new_runs(s, base: str, tracker_ids: list, since: str) -> list:
    """`since`(ISO) 이후에 만들어진 Test Run 을 찾는다. 댓글에 링크로 넣는다."""
    out = []
    for tid in tracker_ids:
        if not tid:
            continue
        r = s.post("%s/api/v3/items/query" % base,
                   json={"queryString": "tracker.id IN (%s)" % tid,
                         "page": 1, "pageSize": 100}, timeout=TIMEOUT)
        if not r.ok:
            continue
        for it in r.json().get("items") or []:
            d = s.get("%s/api/v3/items/%d" % (base, it["id"]), timeout=TIMEOUT)
            if not d.ok:
                continue
            f = d.json()
            if (f.get("createdAt") or "") < since:
                continue
            if (f.get("parent") or {}).get("id"):        # 자식은 부모만 링크한다
                continue
            res = [x.get("name") for x in (f.get("resolutions") or [])]
            out.append((it["id"], f.get("name"), res[0] if res else None, tid))
    return sorted(out)


def comment(s, base: str, item_id: int, text: str):
    """댓글은 **multipart/form-data** 다 — JSON 을 보내면 415 로 거부된다 [실측].
    다른 쓰기 API 는 전부 JSON 이라 이것만 다를 지 몰랐다."""
    r = s.post("%s/api/v3/items/%d/comments" % (base, item_id),
               files={"comment": (None, text), "commentFormat": (None, "Wiki")},
               timeout=TIMEOUT)
    return check(r, "항목 %d 댓글" % item_id)


def move_status(s, base: str, item_id: int, want: str):
    """워크플로가 허용하는 전이만 쓴다. 없으면 조용히 넘긴다 —
    상태를 못 바꿨다고 결과 기록까지 실패시킬 이유가 없다."""
    r = s.get("%s/api/v3/items/%d/transitions" % (base, item_id), timeout=TIMEOUT)
    if not r.ok:
        return None
    for t in r.json() if isinstance(r.json(), list) else []:
        if (t.get("name") or "").lower() == want.lower() or \
           ((t.get("toStatus") or {}).get("name") or "").lower() == want.lower():
            s.put("%s/api/v3/items/%d/fields" % (base, item_id),
                  json={"fieldValues": [{"fieldId": 7, "name": "Status",
                                         "type": "ChoiceFieldValue",
                                         "values": [t["toStatus"]]}]},
                  timeout=TIMEOUT)
            return (t.get("toStatus") or {}).get("name")
    return None


def report(run: dict, steps: list, runs: list, unit_tr, verif_tr) -> str:
    ok = run.get("conclusion") == "success"
    lines = [
        "!! CT 파이프라인 실행 결과",
        "",
        "||항목||값",
        "|실행|[%s|%s]" % (run.get("run_number"), run.get("html_url")),
        "|커밋|{{%s}}" % (run.get("head_sha") or "")[:10],
        "|촉발|%s" % run.get("event"),
        "|결론|%s" % ("__성공__" if ok else "__실패__"),
        "|시각|%s" % datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "",
        "!!! 단계",
        "",
        "||단계||결과",
    ]
    for name, res in steps:
        if name in ("Set up job", "Complete job") or name.startswith("Post "):
            continue
        lines.append("|%s|%s" % (name, {"success": "OK", "failure": "__실패__",
                                        "skipped": "건너뜀"}.get(res, res)))
    lines += ["", "!!! 생성된 Test Run", ""]
    if runs:
        lines.append("||항목||결과||트래커")
        for iid, nm, res, tid in runs:
            kind = "단위" if str(tid) == str(unit_tr) else ("기능" if str(tid) == str(verif_tr) else str(tid))
            lines.append("|[%s|/issue/%s]|%s|%s" % (nm, iid, res or "-", kind))
    else:
        lines.append("(이 실행에서 새로 만들어진 Test Run 을 찾지 못했다)")
    lines += ["", "이 댓글은 {{scripts/cb_run_ct.py}} 가 자동으로 남긴 것이다."]
    return "\n".join(lines)


# ── 실행 ──────────────────────────────────────────────────────────────────────
def run_once(s, base: str, repo: str, task_id: int, unit_tr, verif_tr) -> int:
    d = check(s.get("%s/api/v3/items/%d" % (base, task_id), timeout=TIMEOUT),
              "Task %d 조회" % task_id)
    print("Task %d — %s" % (task_id, d.get("name")))

    since = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S")
    move_status(s, base, task_id, "In progress")
    print("  dispatch 발사...")
    before = fire(repo, task_id)
    run = wait_run(repo, before)
    print("  run %s → %s" % (run["id"], run.get("conclusion")))

    steps = step_results(repo, run["id"])
    made = new_runs(s, base, [unit_tr, verif_tr], since)
    for iid, nm, res, _ in made:
        print("  Test Run %s %s (%s)" % (iid, res, nm[:40]))

    comment(s, base, task_id, report(run, steps, made, unit_tr, verif_tr))
    st = move_status(s, base, task_id,
                     "Completed" if run.get("conclusion") == "success" else "To Verify")
    print("  댓글 기록 완료 · 상태 → %s" % (st or "(변경 없음)"))
    return 0 if run.get("conclusion") == "success" else 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--task", type=int, help="실행할 Task 항목 id")
    ap.add_argument("--watch", action="store_true",
                    help="TASK 트래커를 지켜보며 감시 상태의 CT-RUN 항목을 실행한다")
    ap.add_argument("--task-tracker", help="TASK 트래커 id (없으면 CB_TASK_TRACKER_ID)")
    ap.add_argument("--watch-status", default=os.environ.get("CB_CT_WATCH_STATUS", "In progress"),
                    help="이 상태가 되면 실행한다. 기본 'In progress'")
    ap.add_argument("--interval", type=int, default=15, help="감시 주기(초). 기본 15")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"),
                    help="owner/repo (없으면 GITHUB_REPOSITORY)")
    ap.add_argument("--unit-run-tracker", default=os.environ.get("CB_UNIT_RUN_TRACKER_ID"))
    ap.add_argument("--verif-run-tracker", default=os.environ.get("CB_VERIF_RUN_TRACKER_ID"))
    ap.add_argument("--base-url", default=None)
    a = ap.parse_args()

    if not a.repo:
        raise SystemExit("--repo 또는 GITHUB_REPOSITORY 가 필요하다 (owner/repo).")
    if not (a.task or a.watch):
        raise SystemExit("--task <id> 또는 --watch 중 하나가 필요하다.")

    base = base_url(a.base_url)
    s = session()

    if a.task:
        return run_once(s, base, a.repo, a.task, a.unit_run_tracker, a.verif_run_tracker)

    tt = tracker_id("CB_TASK_TRACKER_ID", a.task_tracker)
    print("TASK 트래커 %s 감시 — 제목 '%s*' · 상태 '%s' · %d초 주기"
          % (tt, WATCH_PREFIX, a.watch_status, a.interval))
    print("Ctrl+C 로 멈춘다.")
    done = set()
    while True:
        r = s.post("%s/api/v3/items/query" % base,
                   json={"queryString": "tracker.id IN (%s)" % tt,
                         "page": 1, "pageSize": 100}, timeout=TIMEOUT)
        if r.ok:
            for it in r.json().get("items") or []:
                if it["id"] in done or not (it.get("name") or "").startswith(WATCH_PREFIX):
                    continue
                f = s.get("%s/api/v3/items/%d" % (base, it["id"]), timeout=TIMEOUT)
                if not f.ok:
                    continue
                st = ((f.json().get("status") or {}).get("name") or "")
                if st.lower() != a.watch_status.lower():
                    continue
                print("\n[%s] 실행 요청 감지 — Task %d"
                      % (datetime.now().strftime("%H:%M:%S"), it["id"]))
                done.add(it["id"])
                try:
                    run_once(s, base, a.repo, it["id"],
                             a.unit_run_tracker, a.verif_run_tracker)
                except SystemExit as e:
                    print("  실패: %s" % e)
                except Exception as e:                    # noqa: BLE001
                    print("  오류: %s" % str(e)[:200])
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
