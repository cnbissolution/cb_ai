#!/usr/bin/env python3
"""Codebeamer 접속 공용 모듈.

**환경변수 이름이 두 갈래로 갈려 있었다.** 이 저장소의 기존 스크립트는
`CB_URL` / `CB_TOKEN` 을 쓰고, codebeamer-mcp 의 `.env` 는
`CB_BASE_URL` / `CB_API_TOKEN` 을 쓴다. 둘 다 받아들여서 CI 시크릿과 로컬
MCP 설정을 그대로 쓸 수 있게 한다. 새 스크립트는 이 모듈만 쓴다.

우선순위: `CB_BASE_URL` > `CB_URL`,  `CB_API_TOKEN` > `CB_TOKEN`
토큰이 없으면 `CB_USERNAME`/`CB_PASSWORD` 또는 `CB_USER`/`CB_PASS` 로 넘어간다.
"""
from __future__ import annotations

import os

import requests

TIMEOUT = int(os.environ.get("CB_TIMEOUT", "60"))


def _first(*names):
    for n in names:
        v = os.environ.get(n)
        if v:
            return v.strip()
    return None


def base_url(explicit=None):
    """`https://<서버>/cb` 형태. 끝의 `/` 는 떼어낸다."""
    url = explicit or _first("CB_BASE_URL", "CB_URL")
    if not url:
        raise SystemExit(
            "Codebeamer 주소가 없다. CB_BASE_URL (또는 CB_URL) 을 설정하라.")
    return url.rstrip("/")


def session():
    s = requests.Session()
    s.headers["Accept"] = "application/json"

    token = _first("CB_API_TOKEN", "CB_TOKEN")
    user = _first("CB_USERNAME", "CB_USER")
    password = _first("CB_PASSWORD", "CB_PASS")

    if token:
        s.headers["Authorization"] = "Bearer %s" % token
    elif user and password:
        s.auth = (user, password)
    else:
        raise SystemExit(
            "인증 정보가 없다. CB_API_TOKEN (또는 CB_TOKEN), "
            "혹은 CB_USERNAME/CB_PASSWORD 를 설정하라.")

    # 사내 인증서를 쓰는 서버가 있어 끌 수 있게 열어둔다. 기본은 검증한다
    s.verify = (os.environ.get("CB_VERIFY_SSL", "true").lower() != "false")
    return s


def check(resp, what):
    if not resp.ok:
        raise RuntimeError("%s 실패: HTTP %d\n%s"
                           % (what, resp.status_code, resp.text[:400]))
    return resp.json() if resp.content else {}


def tracker_id(name, explicit=None):
    """트래커 ID 는 저장소에 적지 않는다. 인자 > 환경변수 순으로 받는다.

    이 저장소는 공개라 실제 ID 가 파일에 들어가면 안 된다. CI 에서는
    GitHub Variables/Secrets 로 주입한다."""
    v = explicit or os.environ.get(name)
    if not v:
        raise SystemExit("%s 가 필요하다 (인자 또는 환경변수)." % name)
    return int(v)
