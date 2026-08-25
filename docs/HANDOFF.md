# 인수인계 (AI RM DevOps 세미나 데모)

다른 계정/다른 PC 에서 이 작업을 이어받기 위한 문서.

> **이 저장소는 공개다.** 실제 트래커/항목 ID, 사내 서버 주소, 계정이 들어간
> 전체본은 `codebeamer-mcp` **비공개** 저장소의 `HANDOFF.md` 에 있다.
> 이 문서는 공개해도 되는 부분만 담는다.

작성: 2026-08-25

---

## 0. 무엇이 어디에 있나

| 덩어리 | 위치 | 이어받기 |
|---|---|---|
| 데모 프로젝트 (코드/문서/CI) | 이 저장소 | `git clone` 하면 끝 |
| **codebeamer-mcp 수정본** | **로컬 디스크만 (`C:\cb\codebeamer-mcp-dist`)** | **아래 2절 필수** |
| Codebeamer 데이터 | 사내 Codebeamer 서버 | 계정만 있으면 보임 |
| 자격증명 (`.env`) | 로컬 | **복사 금지.** 본인 것으로 새로 |

**가장 큰 위험은 두 번째 줄이다.** MCP 수정본은 git 저장소가 아니라
작업한 PC 의 디스크에만 있다. 그 PC 가 사라지면 이번에 고친 것
(itemRefs 파싱, Wiki 포맷, 댓글 415, CSV 라운드트립) 이 전부 사라진다.

---

## 1. 데모 프로젝트 이어받기

```
git clone https://github.com/cnbissolution/cb_ai.git
```

읽는 순서:

1. `README.md` — 전체 구조
2. `docs/DEMO_SCENARIO.md` — 세미나에서 시연할 흐름
3. `REVIEW.md` — **의도적으로 남겨둔 결함 D-1/D-2**. 이건 버그가 아니라
   데모 소재다. 고치지 말 것 (AI 가 정적분석으로 잡아내는 장면에 쓴다)
4. `docs/CI_VERIFICATION_LOG.md` — CI 에서 실제로 관측된 결과

GitHub Pages (코드 인덱스) 가 이미 떠 있다. ALM 에서 코드로 거는 링크는
줄 번호가 아니라 심볼 이름 기준이라 코드가 바뀜도 안 깨진다.
자세한 건 `docs/TRACEABILITY_LINKING.md`.

### 저장소에 없는 것

작업 PC 의 `ptc_cicdct\_archive\` 는 **의도적으로 제외**했다.
개인 메일·고객사명·웹비나 참가자 명단 등 공개하면 안 되는 내용이 들어 있다.
`.gitignore` 로 막아렒다. 새 PC 로 옮길 때도 가져가지 말 것.

---

## 2. codebeamer-mcp 수정본 이어받기 ★

`C:\cb\codebeamer-mcp-dist` 는 git 저장소가 **아니다**. 먼저 이걸 해결해야 한다.

### 2-1. 무엇이 바뀌었나

그 폴더의 `CHANGELOG_20260825.md` 에 전부 적혀 있다. 요약하면:

- **버그 3건** — 항목 목록이 항상 0건으로 나오던 것(`itemRefs` 미처리),
  댓글이 한 번도 성공할 수 없던 것(415), 설명 포맷 기본값이 서버가
  거부하는 `Html` 이던 것
- **도구 3종 추가** — `cb_create_items_bulk`,
  `cb_export_items_csv` / `cb_import_items_csv` (CSV 라운드트립),
  `cb_check_field_values`

바뀜 파일: `src/codebeamer_mcp/` 아래 `formatters.py`, `client.py`,
`server.py`, `server_csv.py`(신규). 원본 백업은 같은 폴더의 `.bak_*` 에 있다.

### 2-2. 옮기는 방법 — 비공개 저장소로 만들 것

`.gitignore` 와 `.env.example`, `setup.ps1` 이 이미 있다.
애초에 저장소가 될 것을 전제로 만들어진 구조인데 `git init` 만 안 되어 있다.

```
cd C:\cb\codebeamer-mcp-dist
git init
git add .
git status          # .env 와 .mcp.json 이 목록에 없는지 반드시 확인
git commit -m "codebeamer-mcp: itemRefs/Wiki/comment 수정 + CSV 라운드트립"
```

`.gitignore` 가 `.env`, `.mcp.json`, `*.bak` 를 이미 막고 있다.
**`git status` 로 눈으로 확인하고 나서** 원격에 올린다.

**반드시 비공개여야 한다.** 사내 서버 URL 과 실제 트래커 ID 가 예제에 섞여 있고,
전체 인수인계 문서(`HANDOFF.md`)도 그 저장소에 들어간다.
사내 GitLab 이든 조직의 private 저장소든 상관없다.

### 2-3. 새 PC 에서 설치

```
git clone <저장소> C:\cb\codebeamer-mcp-dist
cd C:\cb\codebeamer-mcp-dist
copy .env.example .env
notepad .env                 # 값 채우기
powershell -ExecutionPolicy Bypass -File setup.ps1
```

`.env` 항목은 `.env.example` 에 설명이 달려 있다.

**이전 사람의 `.env` 를 복사해 쓰지 말 것.** 감사 로그에 남는 작성자가
엉뚱한 사람이 되고, 계정 회수 시 조용히 깨진다. 본인 계정으로 새로 넣는다.

설치 후 Claude Desktop / Claude Code 를 **재시작**해야 도구가 뜼다.

---

## 3. Codebeamer 현재 상태

프로젝트/트래커의 실제 ID 는 **비공개 저장소의 `HANDOFF.md` 3절**에 있다.
여기서는 상태만 적는다.

- 요구사항 트래커에 **AEB 요구사항 21건**이 올라가 있다.
  같은 트래커에 원래 있던 **템플릿 샘플 35건과 섞여 있다.**
  (넣기 전 "비어 있다"고 판단한 것이 2-1 의 `itemRefs` 버그 때문이었다.)
- description 에는 **요구사항 문장만** 있다. 메타데이터 블록·코드 링크 없음
- `Type`, `ASIL Classification`, `Safety Requirement?`, `Status` 는
  모두 **실제 필드**로 들어갔다

### 알아둘 제약 (실측)

- 요구사항 워크플로가 `New → Draft → In Review → Accepted` 라
  **New 에서 Accepted 로 직행이 안 된다**
- `Safety Requirement?` 는 Draft 상태에서 필수
- `ASIL Classification` 옵션은 `QM/A/B/C/D` (`ASIL-D` 같은 표기 아님)
- `Type` 은 최상위 `categories` 배열로 들어간다 (`type` 키가 아님)
- 설명/댓글 포맷은 `Html` 거부. `Wiki` 또는 `PlainText`
- 프로젝트 생성은 v3 REST 에 없다. UI 로만 (트래커 생성은 API 가능)

나머지는 `CHANGELOG_20260825.md` 3절 표에 정리해둖다.

---

## 4. 남은 작업

우선순위 순.

1. **MCP 를 저장소로 만들기** (2-2). 이게 안 되면 나머지가 의미 없다
2. **MCP 재시작 후 실서버 검증** — 로컬 검증만 마친 상태다
   - `cb_list_tracker_items` 가 실제 건수를 보여주는지
   - `cb_add_comment` 이 실제로 성공하는지 (415 해소 여부)
   - `cb_export_items_csv` → `cb_import_items_csv(dry_run=True)` 왕복
3. **SDD 를 Codebeamer 에 적재** — 지금은 SRS 만 올라가 있다
4. **association 연결** — SDD 적재 후 요구사항 ↔ 코드/설계를
   `is related to` / `is derived from` 으로 연결. 아직 시작 안 함
5. **Test Case 트래커 필드 정규화** — description 에 아직 코드 링크와
   메타데이터가 남아 있다. SRS 와 같은 방식으로 정리 필요
6. **요구사항 승인분을 Accepted 로** — 단계별 전환이라 항목당 3회.
   CSV 도구가 붙었으니 그걸로 처리하는 게 싸다

### 알려진 미해결 결함

- `cb_update_item` 이 읽기 전용 계산 필드를 되돌려 보내 403 이 난다.
  `customFields` 를 명시해 우회 중
- 생성된 MCP 도구들의 `body` 가 `dict` 로만 타이핑되어 **배열 본문을 못 보낸다**.
  `PUT /items/fields`(일괄 필드 수정)가 막혀 있어 항목별 호출을 하게 된 원인.
  `server_generated.py` 는 `generate_tools.py` 가 생성하므로 **생성기를 고쳐야** 한다
- `scripts/upload_to_codebeamer.py`, `scripts/agentic_analyzer.py` 가
  아직 `Html` 포맷을 보낸다 → `Wiki` 로 고쳐야 함
- 커버리지 HTML 리포트가 Codebeamer 에 업로드되지 않는다.
  `--html-details` 는 파일을 여러 개 만드는데 워크플로는 하나만 챙긴다
- `ci/cicd-ct.yml`, `.github/PERMISSION_TEST.md` 는 삭제 대상 잔재

---

## 5. 절대 공유하면 안 되는 것

- `codebeamer-mcp-dist\.env` — 실제 계정/비밀번호
- `ptc_cicdct\_archive\` — 개인 메일, 고객사명, 참가자 명단
- MCP 저장소를 **공개**로 만드는 것 — 내부 서버 URL 과 트래커 ID 가 들어 있다
