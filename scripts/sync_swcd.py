#!/usr/bin/env python3
"""소스코드 유닛을 SWCD 항목으로 올리고 상세설계(SDD)에 참조 필드로 잇는다.

`link_code.py` 와 목적은 같고 **표현 방식이 다르다.**

  link_code.py   SDD 항목 → 코드 URL,  association(`derived`)
  sync_swcd.py   코드 유닛 → SWCD 항목 → SDD 항목,  **참조 필드**

association 을 참조 필드로 바꾸는 이유는 하나다. **association 은
upstream/downstream 이 되지 않아 추적성 리포트와 Traceability Browser 에
나오지 않는다** (docs/KNOWLEDGE.md 실측). 항목 화면에서 사람이 눌러 보는 데는
쓸 수 있지만, SDD 쪽에서 하위 코드를 트리로 펼치거나 추적률로 세는 것은 안 된다.
참조 필드는 둘 다 된다.

SWCD 항목에는 두 가지를 쓴다.

  * 상위 SDD 참조 필드 (`--upstream-field`)   추적성의 본체
  * `Github_URL` WikiText 필드 (`--url-field`) 라벨이 유닛 ID 인 소스 링크

두 번째는 추적성 화면에서 항목 → 소스로 바로 넘어가라고 두는 것이다. 이 코드비머에는
URL 전용 필드 타입이 없어 WikiText 에 `[SCS-AF-001|https://...]` 로 넣는다.
그 필드가 없는 트래커에 대고 돌려야 하면 `--url-field 0` 으로 끈다.

방향은 **상향식(bottom-up)** 이다. 링크는 SWCD 항목에만 쓰고 SDD 항목은 건드리지
않는다. 상위 문서를 수정하지 않으므로 베이스라인이 흔들리지 않고, 역방향은
Codebeamer 가 자동으로 보여준다. 이 때문에 SWCD 트래커에 SDD 를 가리키는
참조 필드가 하나 있어야 한다 (`--upstream-field`).

입력은 `build_symbol_map.py` 가 만든 `unit_index.json` 을 그대로 쓴다. 별도 파서를
만들지 않는다 — 그쪽이 이미 `@unit <유닛ID> -> <SDD ID>...` 를 파싱해 유닛 ID·심볼·
파일·줄·GitHub 퍼머링크·상위 SDD 목록을 모두 담고 있다.

사용:
  set CB_BASE_URL=https://<서버>/cb        (CB_URL 도 받는다)
  set CB_API_TOKEN=...                     (CB_TOKEN, 계정/비밀번호도 받는다)

  python scripts/sync_swcd.py --swcd-tracker 12345 --swdd-tracker 67890 --dry-run
  python scripts/sync_swcd.py --swcd-tracker 12345 --swdd-tracker 67890

멱등이다. 유닛 ID(`SCS-*`)를 unique key 로 삼아 기존 항목을 찾고, 없으면 만들고
있으면 바뀐 필드만 고친다. 매 푸시마다 같은 유닛이 중복 생성되지 않는다.

종료 코드: 해석 못 한 SDD ID 나 API 실패가 하나라도 있으면 1.
트래커 ID 는 저장소에 적지 않는다 — 인자나 환경변수로만 받는다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cb_common import TIMEOUT, base_url, check, session, tracker_id  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# 항목 제목의 첫 토큰이 unique key 다. `SCS-AF-001 Aeb_Init` 에서 `SCS-AF-001`.
KEY_RE = re.compile(r"^([A-Z]{2,}-[A-Z0-9]+-\d+)")


def load_index(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit("%s 가 없다. build_symbol_map.py 를 먼저 돌려라." % path)
    return json.loads(path.read_text(encoding="utf-8"))


def all_items(s, base: str, tid: int) -> list:
    """트래커의 모든 항목. 페이지를 끝까지 넘긴다.

    `GET /trackers/{id}/items` 는 전체 항목이 아니라 **itemRefs** 로 답한다.
    키 이름을 하나만 보면 조용히 0건이 되므로 둘 다 본다.
    """
    out, page = [], 1
    while True:
        r = check(s.get("%s/api/v3/trackers/%d/items" % (base, tid),
                        params={"page": page, "pageSize": 50}, timeout=TIMEOUT),
                  "트래커 %d 항목 조회" % tid)
        refs = r.get("itemRefs") or r.get("items") or []
        out += refs
        if len(refs) < 50:
            return out
        page += 1


def key_map(items: list) -> dict:
    """제목 첫 토큰 → 항목 id."""
    out = {}
    for it in items:
        m = KEY_RE.match((it.get("name") or "").strip())
        if m:
            out.setdefault(m.group(1), it["id"])
    return out


def describe(unit_id: str, u: dict) -> str:
    """SWCD 항목 본문. 코드로 돌아가는 링크가 핵심이다."""
    lines = [
        "이 항목은 소스코드 유닛을 나타내며 **파이프라인이 자동 생성**한다.",
        "직접 편집하지 마라 — 다음 동기화에서 덮인다.", "",
        "||항목||값",
        "|유닛 ID|%s" % unit_id,
        "|심볼|%s" % (u.get("symbol") or "-"),
        "|파일|%s (%s 줄)" % (u.get("file") or "-", u.get("line") or "-"),
        "|상위 설계|%s" % ", ".join(u.get("designs") or []) or "-",
        "",
    ]
    if u.get("url"):
        lines += ["[GitHub 에서 이 코드 보기|%s]" % u["url"], ""]
    return "\n".join(lines)


def ref_value(field_id: int, name: str, ids: list) -> dict:
    """참조 필드 값. `TrackerItemReference` 여야 한다 — `ItemReference` 는 거부된다."""
    return {"fieldId": field_id, "name": name, "type": "ChoiceFieldValue",
            "values": [{"id": i, "type": "TrackerItemReference"} for i in sorted(ids)]}


def url_value(field_id: int, name: str, unit_id: str, url: str) -> dict:
    """`Github_URL` 필드 값 — 라벨이 유닛 ID 인 소스 링크.

    이 코드비머에는 URL 전용 필드 타입이 없다 [실측: Text(0) 와 WikiText(10) 뿐].
    WikiText 에 `[라벨|주소]` 로 넣으면 하이퍼링크로 렌더되고, 그 필드를 트래커 뷰의
    열로 세우면 추적성 화면에서 항목 → 소스로 바로 넘어간다.
    """
    return {"fieldId": field_id, "name": name, "type": "WikiTextFieldValue",
            "value": "[%s|%s]" % (unit_id, url)}


def put_fields(s, base: str, item_id: int, values: list):
    """부분 수정. `PATCH /items/{id}` 는 405 다 — `PUT /items/{id}/fields` 를 쓴다."""
    r = s.put("%s/api/v3/items/%d/fields" % (base, item_id),
              json={"fieldValues": values}, timeout=TIMEOUT)
    if r.status_code == 400 and "Mandatory" in r.text:
        # 필수 필드가 비어 있으면 다른 필드 수정도 함께 막힌다. 오늘 실측:
        # `Mandatory "Safety Requirement?" value is missing`
        raise RuntimeError(
            "항목 %d: 필수 필드가 비어 있어 거부됐다. 트래커의 필수 필드를 "
            "채우거나 필수 지정을 풀어야 한다.\n  %s" % (item_id, r.text[:300]))
    return check(r, "항목 %d 필드 수정" % item_id)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--swcd-tracker", help="SWCD 트래커 id "
                                           "(없으면 CB_SWCD_TRACKER_ID)")
    ap.add_argument("--swdd-tracker", help="상세설계 트래커 id "
                                           "(없으면 CB_SWDD_TRACKER_ID)")
    # `os.environ.get(k, default)` 를 쓰면 안 된다. GitHub Actions 는 설정되지 않은
    # 변수를 `env:` 로 넘길 때 **빈 문자열**로 넣는다. 그러면 키가 존재하므로
    # default 가 안 먹고, `int("")` 은 ValueError 로 **스크립트가 시작도 못 하고
    # 죽는다** [실측]. 이름 쪽은 더 나쁘게 — 조용히 빈 이름이 API 로 나간다.
    # `or` 로 받아 빈 값을 같이 걸러낸다.
    ap.add_argument("--upstream-field", type=int,
                    default=int(os.environ.get("CB_SWCD_UPSTREAM_FIELD") or 17),
                    help="SWCD 항목에서 SDD 를 가리키는 참조 필드 id. 기본 17")
    ap.add_argument("--upstream-field-name",
                    default=(os.environ.get("CB_SWCD_UPSTREAM_FIELD_NAME")
                             or "Linked SW Detailed Design"))
    ap.add_argument("--url-field", type=int,
                    default=int(os.environ.get("CB_SWCD_URL_FIELD") or 10003),
                    help="소스 링크를 넣을 WikiText 필드 id. 0 이면 쓰지 않는다. 기본 10003")
    ap.add_argument("--url-field-name",
                    default=(os.environ.get("CB_SWCD_URL_FIELD_NAME") or "Github_URL"))
    ap.add_argument("--index", default="unit_index.json")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="아무것도 쓰지 않고 무엇이 바뀔지만 보여준다")
    a = ap.parse_args()

    swcd = tracker_id("CB_SWCD_TRACKER_ID", a.swcd_tracker)
    swdd = tracker_id("CB_SWDD_TRACKER_ID", a.swdd_tracker)
    base, s = base_url(a.base_url), session()

    index = load_index(ROOT / a.index)
    units = {k: v for k, v in index.items() if v.get("designs")}
    skipped = sorted(set(index) - set(units))
    print("유닛 %d개 중 상위 설계가 지정된 것 %d개" % (len(index), len(units)))
    if skipped:
        print("  상위 설계 없음(건너뜀): %s" % ", ".join(skipped))

    # SDD 키 → 숫자 항목 id. 참조 필드는 사람이 읽는 키가 아니라 숫자 id 를 받는다.
    sdd = key_map(all_items(s, base, swdd))
    print("상세설계 항목 %d개를 키로 색인했다" % len(sdd))

    have = key_map(all_items(s, base, swcd))
    print("SWCD 트래커에 이미 있는 유닛 %d개" % len(have))

    created = updated = same = 0
    problems = []

    for unit_id in sorted(units):
        u = units[unit_id]
        want = [sdd[d] for d in u["designs"] if d in sdd]
        missing = [d for d in u["designs"] if d not in sdd]
        if missing:
            problems.append("%s: 상세설계 항목을 못 찾았다 — %s"
                            % (unit_id, ", ".join(missing)))
            if not want:
                continue

        # 심볼이 없는 유닛도 있다 (헤더의 매크로·타입 정의 등은 ctags 심볼이 아니다).
        # 제목이 ID 하나로 끝나면 목록에서 무엇인지 알 수 없으므로 파일·줄로 떨어진다.
        label = u.get("symbol") or u.get("unit_key")
        if not label:
            label = "%s:%s" % (Path(u.get("file") or "?").name, u.get("line") or "?")
        title = "%s %s" % (unit_id, label)
        body = describe(unit_id, u)
        ref = ref_value(a.upstream_field, a.upstream_field_name, want)
        values = [ref]
        # 링크는 유닛에 url 이 있을 때만. 필드 id 를 0 으로 주면 통째로 끈다 —
        # 그 필드가 없는 트래커에 대고 돌릴 수도 있어야 한다.
        link = None
        if a.url_field and u.get("url"):
            link = url_value(a.url_field, a.url_field_name, unit_id, u["url"])
            values.append(link)

        try:
            if unit_id not in have:
                if a.dry_run:
                    print("  생성 예정  %s → SDD %s" % (title.strip(), want))
                    created += 1
                    continue
                r = check(s.post("%s/api/v3/trackers/%d/items" % (base, swcd),
                                 json={"name": title.strip(), "description": body,
                                       "descriptionFormat": "Wiki"},
                                 timeout=TIMEOUT), "%s 생성" % unit_id)
                iid = r["id"]
                put_fields(s, base, iid, values)
                print("  생성        %s (id %d) → SDD %s" % (unit_id, iid, want))
                created += 1
            else:
                iid = have[unit_id]
                if a.dry_run:
                    print("  갱신 예정  %s (id %d) → SDD %s" % (unit_id, iid, want))
                    updated += 1
                    continue
                cur = check(s.get("%s/api/v3/items/%d/fields" % (base, iid),
                                  timeout=TIMEOUT), "항목 %d 필드 조회" % iid)
                fields = {f.get("fieldId"): f
                          for f in cur.get("editableFields", [])}
                now = fields.get(a.upstream_field) or {}
                up_same = sorted(v["id"] for v in (now.get("values") or [])) == sorted(want)
                # 링크도 비교한다. 코드가 움직이면 퍼머링크의 줄 범위가 바뀌므로,
                # 상위 SDD 만 보면 "변화 없음" 으로 넘겨 링크가 낡은 채 남는다.
                url_same = True
                if link:
                    url_same = (fields.get(a.url_field) or {}).get("value") == link["value"]
                if up_same and url_same:
                    print("  변화 없음  %s (id %d)" % (unit_id, iid))
                    same += 1
                    continue
                put_fields(s, base, iid, values)
                print("  갱신        %s (id %d) → SDD %s" % (unit_id, iid, want))
                updated += 1
        except Exception as e:                        # noqa: BLE001
            problems.append("%s: %s" % (unit_id, e))

    print("\n생성 %d · 갱신 %d · 변화 없음 %d · 문제 %d"
          % (created, updated, same, len(problems)))
    for p in problems:
        print("  [문제] %s" % p)
    if problems:
        # CI 가 조용히 초록으로 지나가면 추적성이 거짓이 된다.
        print("\n추적 연결이 완전하지 않다. 위 문제를 해결하고 다시 돌려라.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
