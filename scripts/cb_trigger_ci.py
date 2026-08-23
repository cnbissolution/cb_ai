#!/usr/bin/env python3
"""
Codebeamer -> GitHub Actions 트리거 브릿지 (REVIEW.md G-1 해결)

문제:
  Codebeamer 에는 GitHub Actions 를 직접 촉발하는 내장 기능이 없다.
  이 때문에 통상 Jenkins 를 중간에 두고 (Codebeamer 플러그인 -> Jenkins -> 빌드)
  구성하지만, 유지보수 포인트가 늘고 Jenkins 를 계속 떠안게 된다.

해법:
  GitHub REST API 의 repository_dispatch 를 호출하는 얇은 스크립트 하나로,
  플러그인 개발 없이 "ALM 이 CI 를 촉발하는" 방향을 성립시킨다.
  이것이 파이프라인의 on.repository_dispatch 진입점과 짝을 이룬다.

배선 방법 (세 가지 중 택 1):
  (A) Codebeamer 워크플로우 전환 액션 -> "Execute Script" 로 본 스크립트 호출
      가장 즉각적. 요구사항이 Approved 로 전환될 때 CI 를 돌리는 시나리오에 적합.
  (B) Codebeamer 아웃고잉 웹훅 -> 중계 서버(Lambda/Functions) -> 본 로직
      Codebeamer 서버에 스크립트 실행 권한을 주기 어려운 환경에서 사용.
  (C) 주기 폴링 브릿지: cron 이 Codebeamer 를 조회해 신규 Test Set 실행 요청을 감지
      워크플로우 수정 권한이 없을 때의 최후 수단.

사용:
  python3 scripts/cb_trigger_ci.py \
      --event-type codebeamer-test-request \
      --cb-item-id 10254 \
      --ref main

환경변수:
  GITHUB_REPOSITORY   owner/repo (예: cnbissolution/cb_ai)
  GITHUB_PAT          repo 스코프를 가진 Personal Access Token
                      (fine-grained 토큰은 "Contents: write" 권한 필요)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import requests

TIMEOUT = 30
GITHUB_API = "https://api.github.com"

VALID_EVENT_TYPES = (
    "codebeamer-test-request",          # Test Set 실행 요청
    "codebeamer-requirement-approved",  # 요구사항 승인 -> 회귀 시험 재실행
)


def dispatch(repo, pat, event_type, payload, dry_run=False):
    """POST /repos/{owner}/{repo}/dispatches

    성공 시 HTTP 204 (본문 없음). 실패 원인 대부분은
      401/403 -> PAT 스코프 부족
      404      -> 저장소명 오타 또는 PAT 가 해당 저장소를 못 봄
                  (fine-grained 토큰에서 흔함)
      422      -> event_type 이 워크플로우의 types 목록에 없음
    """
    url = "%s/repos/%s/dispatches" % (GITHUB_API, repo)
    body = {"event_type": event_type, "client_payload": payload}

    if dry_run:
        print("[dry-run] POST %s" % url)
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return 0

    resp = requests.post(
        url,
        headers={
            "Authorization": "Bearer %s" % pat,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=body,
        timeout=TIMEOUT,
    )

    if resp.status_code == 204:
        print("[ok] 파이프라인 트리거 완료: %s (event_type=%s)" % (repo, event_type))
        return 0

    sys.stderr.write("[FAIL] dispatch 실패: HTTP %d\n" % resp.status_code)
    sys.stderr.write("       %s\n" % resp.text[:500])
    if resp.status_code == 404:
        sys.stderr.write("       -> 저장소명 또는 PAT 접근 권한을 확인하십시오.\n")
    elif resp.status_code == 422:
        sys.stderr.write("       -> 워크플로우의 repository_dispatch.types 에 "
                         "'%s' 가 등록되어 있는지 확인하십시오.\n" % event_type)
    return 1


def main():
    ap = argparse.ArgumentParser(description="Codebeamer -> GitHub Actions 트리거")
    ap.add_argument("--event-type", default="codebeamer-test-request",
                    choices=VALID_EVENT_TYPES)
    ap.add_argument("--cb-item-id", default="",
                    help="CI 결과를 연결할 Codebeamer 항목 ID (Test Set / Bug / Requirement)")
    ap.add_argument("--cb-project-id", default="", help="Codebeamer 프로젝트 ID")
    ap.add_argument("--ref", default="main", help="빌드 대상 브랜치")
    ap.add_argument("--triggered-by", default="codebeamer-workflow",
                    help="촉발 주체 (감사 추적용)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY")
    pat = os.environ.get("GITHUB_PAT")

    if not args.dry_run:
        if not repo:
            sys.stderr.write("GITHUB_REPOSITORY 환경변수가 필요합니다 (owner/repo).\n")
            return 2
        if not pat:
            sys.stderr.write("GITHUB_PAT 환경변수가 필요합니다.\n")
            return 2

    payload = {
        "cb_item_id": args.cb_item_id,
        "cb_project_id": args.cb_project_id,
        "ref": args.ref,
        "triggered_by": args.triggered_by,
    }

    return dispatch(repo or "owner/repo", pat or "", args.event_type,
                    payload, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
