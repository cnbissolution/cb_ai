# 개발 정리 — 무엇을 만들었고, 왜 그렇게 했나

발표 자료 작성을 위해 흩어져 있던 내용을 한 곳에 모은 문서.
각 항목의 상세 근거는 오른쪽에 적힌 파일을 참조.

작성: 2026-08-25

---

## 1. 한 장 요약

Codebeamer ALM 에서 **요구사항 → 설계 → 구현 → 시험 → 커버리지 → 컴플라이언스**
전 과정을 잇되, 그 연결을 사람이 아니라 **CI 와 AI 가 유지하게** 만든 것.

기존 자료(Gemini 산출)는 **빌드조차 되지 않는 상태**였다. 결함 7건과 전략 갭 4건을
식별해 고치고, 그 과정에서 **ALM 연동 도구(MCP) 자체의 버그 3건**도 드러나 함께 수정했다.

핵심은 세 가지다.

1. **안 끊어지는 추적성** — ALM 에서 코드로 거는 링크를 줄 번호가 아닌 심볼 이름 기준으로
2. **양방향 연계** — 코드→ALM 뿐 아니라 **ALM→CI 트리거**까지 (Jenkins 없이)
3. **실패를 감추지 않는 파이프라인** — 시험이 깨져도 증적은 올라가고, 판정은 별도 게이트가

---

## 2. 개발 산출물

### 2-1. 대상 소프트웨어 (데모 소재)

| 산출물 | 내용 |
|---|---|
| `src/Aeb_FusionEngine.c` | AEB 센서 퓨전 — TTC 계산, 제동 판단 |
| `src/Aeb_Interfaces.h` | **함수 포인터 기반** 센서/액추에이터 인터페이스 |
| `src/Std_Types.h` | AUTOSAR 타입 최소 정의 — **신규** (없어서 빌드 불가였음) |
| `test/test_Aeb_FusionEngine.cpp` | 단위시험 (GTest/GMock) 4 케이스 |
| `test/Aeb_TestHarness.c` | **SIL 하네스 — 신규.** Mock 센서 + ctypes 노출 래퍼 |
| `test/test_functional_scenario.py` | 기능시험 시계열 6 케이스 |

인터페이스를 함수 포인터로 둔 덕에 **같은 C 코드가 GTest(C++)와 pytest(ctypes) 양쪽에서**
시험된다. 하드웨어 없이 두 층위의 검증이 가능하다.

### 2-2. CI/CD 파이프라인

| 산출물 | 내용 |
|---|---|
| `.github/workflows/cicd-ct.yml` | 빌드 → 단위시험 → SIL → 커버리지 → ALM 업로드 → 판정 게이트 |
| `.github/workflows/pages.yml` | Doxygen → 심볼 인덱스 → 리다이렉트 → Pages 배포 |
| `Doxyfile` | `@req`/`@verifies`/`@satisfies` 를 xrefitem 으로 매핑 |

### 2-3. 추적성 인프라 (이번 작업의 차별점)

| 산출물 | 내용 |
|---|---|
| `scripts/build_symbol_map.py` | ctags 로 심볼→파일:라인 인덱싱 (정규식 폴백 포함) |
| `scripts/generate_redirects.py` | `sym/<경로>/<심볼>/`, `req/<ID>/` 리다이렉트 페이지 생성 |
| `docs/TRACEABILITY_LINKING.md` | 링크 체계 설계 문서 |
| `docs/generated/CODE_INDEX.md` | 자동 생성 코드 인덱스 |

### 2-4. ALM 연동

| 산출물 | 내용 |
|---|---|
| `scripts/upload_to_codebeamer.py` | 시험 결과/커버리지 → Codebeamer Test Run. `--check-schema` 프리플라이트 |
| `scripts/cb_trigger_ci.py` | **Codebeamer → GitHub `repository_dispatch`** (G-1 해결) |
| `scripts/agentic_analyzer.py` | 실패 분석 (Claude Opus 5, 구조화 출력) → ALM 코멘트 |
| `scripts/seed_codebeamer_demo.py` | 데모 데이터 시더 (dry-run 우선) |

### 2-5. codebeamer-mcp 개선 ★ 저장소 밖

**이 저장소에 없다.** `C:\cb\codebeamer-mcp-dist` 에 있고 아직 git 저장소가 아니다.
상세는 그 폴더의 `CHANGELOG_20260825.md`.

| 구분 | 내용 |
|---|---|
| 버그 수정 | 항목 목록이 **항상 0건**으로 나오던 것 (`itemRefs` 미처리) |
| | 댓글이 **한 번도 성공할 수 없던** 것 (415 — JSON 불가, 필드명도 오류) |
| | 설명 포맷 기본값이 서버가 **거부하는 `Html`** 이던 것 |
| 도구 추가 | `cb_export_items_csv` / `cb_import_items_csv` — **CSV 라운드트립** |
| | `cb_create_items_bulk` — 일괄 생성 (확인 1회로 N건) |
| | `cb_check_field_values` — 대량 쓰기 전 선택지 검증 |

첫 번째 버그는 **에러가 아니라 조용히 틀린 답**을 주는 유형이었다. 이걸 믿고
"트래커가 비어 있다"고 판단해 데모 데이터를 넣었는데, 실제로는 템플릿 샘플 35건이
이미 있어서 섞였다. **도구가 틀리면 판단이 틀린다**는 사례로 발표에 쓸 만하다.

### 2-6. Codebeamer 적재 결과

요구사항 **21건**을 실제 트래커에 올렸다 (기존 템플릿 35건과 같은 트래커, 섞임).

- description 에는 **요구사항 문장만**. 메타데이터 블록·코드 링크 없음
- `Type`, `ASIL Classification`, `Safety Requirement?`, `Status` 는 **실제 필드**로

---

## 3. 기술 고려사항 — 쟁점과 선택

발표의 알맹이. 각 행이 하나의 슬라이드가 될 수 있다.

| # | 쟁점 | 선택 | 왜 | 근거 |
|---|---|---|---|---|
| 1 | ALM→코드 링크가 코드 수정마다 깨진다 | **심볼 기준 리다이렉트** (`sym/<파일>/<심볼>/`) | 줄 번호는 커밋마다 밀리지만 심볼 이름은 안 밀린다. 링크를 코드가 아니라 인덱스가 따라간다 | `TRACEABILITY_LINKING.md` |
| 2 | ALM 에서 CI 를 어떻게 촉발하나 (Jenkins 없이) | **`repository_dispatch`** | 워크플로 액션이 GitHub API 를 직접 호출. 중간 서버 불필요 | REVIEW G-1 |
| 3 | 시험이 실패하면 증적이 유실된다 | `continue-on-error` + `if: always()` + **별도 판정 게이트** | 실패해도 증적은 ALM 에 올라가야 한다. 통과/실패 판정은 마지막 게이트가 `::error::` 로 | REVIEW D-3 ⑤ |
| 4 | 같은 소스를 두 번 계측하면 `.gcda` 가 충돌 | `build/unit` 과 `build/sil` **분리** | 단위시험과 SIL 이 같은 오브젝트를 공유하면 커버리지 데이터가 깨진다 | REVIEW D-3 ⑥ |
| 5 | ALM 연동을 REST 로 할까 MCP 로 할까 | **역할 분담** — 파이프라인=REST, 대화형 시연=MCP | 무인 실행은 결정적이어야 하고, 시연은 대화형이어야 설득된다 | REVIEW G-4 |
| 6 | 실패 분석 LLM 선택 | **Claude Opus 5 + 구조화 출력** | JSON 스키마를 강제해 파싱 실패를 없앤다 | REVIEW D-6 |
| 7 | 요구사항 21건을 어떻게 적재하나 | **CSV 라운드트립** (MCP 도구 신규) | 항목별 호출은 100회를 넘었다. 원본이 이미 CSV 인데 손으로 옮겨 적은 셈 | `CHANGELOG_20260825.md` |
| 8 | 결함 D-1/D-2 를 고칠까 | **고치지 않고 보존** | AI 가 요구사항-코드 불일치와 도달불가 코드를 잡아내는 장면이 데모의 핵심 | `DEMO_SCENARIO.md` |
| 9 | 커버리지 100% 가 안 나온다 | **요구사항 문제로 규명** | 미실행 분기 13개를 3개 요구사항으로 분해. 게으름이 아니라 요구사항 미승인이 원인 | `CI_VERIFICATION_LOG.md` 3절 |
| 10 | 다국어 인스턴스에서 옵션명이 깨진다 | `--check-schema` **프리플라이트** | 영문 옵션명을 하드코딩하면 다른 고객사에서 깨진다. 전송 전 실제 스키마와 대조 | `CI_VERIFICATION_LOG.md` 4절 |

---

## 4. 실측 수치

발표에서 숫자로 말할 수 있는 것만.

| 지표 | 값 |
|---|---|
| 라인 커버리지 | **100.00%** (44/44) |
| 브랜치 커버리지 | **63.89%** (23/36) |
| 미실행 분기 | 13개 — **전부 3개 요구사항으로 설명됨** |
| └ SRS-AEB-205 (제안, 미승인) | 4개 — 요구사항 승인되면 시험 가능 |
| └ SRS-AEB-206 (제안, 미승인) | 8개 — 위와 동일 |
| └ SRS-AEB-306 (보류, 도달불가) | 1개 — **시험으로 해결 불가. 코드를 고쳐야** |
| SIL 기능시험 | 6건 전부 통과 (로컬·CI 양쪽) |
| 단위시험 | 2건 실패 — **의도적 보존**, CI 에서 재현 확인 |

### 이 수치가 발표에서 갖는 의미

"커버리지 100% 를 못 채웠다"가 아니라 **"못 채운 이유가 전부 요구사항에서 설명된다"** 는
것이 요점이다. 13개 분기 중 12개는 요구사항이 아직 승인되지 않아서고, 1개는
코드가 도달 불가라서다. 커버리지 미달이 **품질 지표가 아니라 요구사항 관리 지표**로
바뀌는 지점이다.

도달불가(SRS-AEB-306) 는 **두 가지 독립적인 방법으로 같은 결론**에 도달했다:
ctypes 스윕 분석(`d2_dead_branch_probe.py`)과 gcov 의 `L49 branch 1 taken 0`.

---

## 5. CI 가 아니었으면 못 잡았을 것

발표에 쓸 만한 사례.

**ctags 가 `TEST_F` 를 함수로 오인했다.** 로컬에는 ctags 가 없어 정규식 폴백만
돌았기 때문에 재현되지 않았고, CI 에서야 드러났다. 요구사항 페이지마다 `TEST_F`
라는 가짜 심볼 행이 섞였다.

> 교훈: **폴백 경로만 돌려보고 "검증했다"고 하면 안 된다.**
> 주 경로와 폴백 경로는 서로 다른 결과를 낸다.

---

## 6. 아직 검증하지 못한 것

발표에서 과장하지 않기 위해 명시한다.

| 항목 | 사유 |
|---|---|
| `automatedtestruns` **요청 본문 스키마** | 서버에 OpenAPI 엔드포인트 미노출. 필드명은 트래커 스키마로 확정했으나 봉투 형태는 문서 기준 추정 |
| 실제 Test Run 생성 | Secrets 미설정 |
| AI 실패 분석 실행 | `ANTHROPIC_API_KEY` 미설정 |
| ALM→CI `repository_dispatch` | Codebeamer 워크플로 액션 배선 필요 |
| MCP 신규 도구 실서버 동작 | 로컬 검증만 완료. **MCP 재시작 후 확인 필요** |

---

## 7. 더 읽을 것

| 주제 | 파일 |
|---|---|
| 기존 자료 검토 + 결함/갭 전체 | `REVIEW.md` |
| CI 실측 결과와 근거 | `docs/CI_VERIFICATION_LOG.md` |
| 시연 흐름 (말할 것 포함) | `docs/DEMO_SCENARIO.md` |
| 추적성 링크 설계 | `docs/TRACEABILITY_LINKING.md` |
| 요구사항 / 설계 | `docs/SRS_AEB_Requirements.md`, `docs/SDD_AEB_Design.md` |
| MCP 개선 상세 | `C:\cb\codebeamer-mcp-dist\CHANGELOG_20260825.md` (저장소 밖) |
| 인수인계 | `docs/HANDOFF.md` |
