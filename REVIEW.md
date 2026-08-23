# Gemini 기존 자료 검토 결과 (취/버림 판정 + 결함 리스트)

- 검토일: 2026-08-23
- 검토 대상: Gemini 세션 산출물 13개 파일 (로컬 `ptc_cicdct/`)
- 목적: **AI RM DevOps 세미나 — "AI 도입을 통한 CI/CD/CT 연계 방안"** 데모용 샘플 프로젝트 기반 자료 확정

---

## 1. 총평

**뼈대는 쓸 만하고, 실행은 안 된다.**

- 잘 잡힌 것: AEB라는 소재 선정, 함수 포인터 기반 DIP 설계(→ Mock 주입 가능),
  SRS→SDD→코드→단위/기능시험→커버리지→ALM 리포팅으로 이어지는 **V-모델 데모 서사**,
  "Jenkins 없이 GitHub Actions + REST API" 라는 경량 아키텍처 방향.
- 안 되는 것: **당시 상태로는 단 한 줄도 빌드/실행되지 않았다.** 파일 누락 3건,
  테스트 실패 유발 결함 1건, 도달 불가 코드 1건, 존재하지 않는 API 엔드포인트 1건,
  동작하지 않는 스크립트 인자 처리 1건. 라이브 데모에 그대로 올리면 반드시 사고 난다.
- 방향 오류: 원래 제기된 **"Codebeamer → GitHub 트리거가 없다"** 는 문제를
  Gemini 답변은 **한 번도 해결하지 않았다.** (아래 G-1)

---

## 2. 취(取) — 살려서 재배치한 자료

| 원본 파일 | 이동/재구성 결과 | 판정 근거 |
|---|---|---|
| `Aeb_Interfaces.h` | `src/Aeb_Interfaces.h` | 데모의 핵심 자산. 함수 포인터 인터페이스가 있어야 gmock 주입·SIL 랩핑이 성립 |
| `Aeb_FusionEngine.c` | `src/Aeb_FusionEngine.c` | MISRA 방어 로직 적용 최종본. 요구사항 15건의 구현 근거 |
| `test_Aeb_FusionEngine.cpp` | `test/test_Aeb_FusionEngine.cpp` | 경계값 페어(1.8s→1.44s) 설계가 우수. **단 D-1 존재** |
| `gemini-code-1787464875711.py` | `test/test_functional_scenario.py` | SIL 기능시험 시나리오 아이디어는 유효. **하네스 구현 필요(D-4)** |
| `gemini-code-1787464873417.yaml` | `ci/cicd-ct.yml` | 파이프라인 5단계 골격 유효. **D-3 수정 필수** |
| `gemini-code-1787464866780.py` | `scripts/upload_to_codebeamer.py` | 방향은 맞음. **엔드포인트 전면 교체 필요(D-5)** |
| `gemini-code-1787464858524.py` | `scripts/agentic_analyzer.py` | AI 연계 데모의 핵심. **재작성 수준 수정 필요(D-6)** |
| `gemini-code-1787464863099.txt` | `docs/diagrams/agentic_pipeline.puml` | Agentic 파이프라인 시퀀스. 발표 장표에 그대로 사용 가능 |
| (대화 내 표) SRS 2개 버전 | `docs/SRS_AEB_Requirements.md` + `.csv` | 15항목 상세판 + 8항목 ASIL판을 **병합**하여 완전판 생성 |
| (대화 내 표) SDD | `docs/SDD_AEB_Design.md` | Data Dictionary / 인터페이스 / 페일세이프 설계 보존 |
| (대화 내 표) 추적성 매트릭스 | `docs/Traceability_Matrix.csv` | **실제 파일의 라인 번호로 재검증**하여 재작성 (원본은 개선 전 코드 기준이라 라인 불일치) |
| (대화 내) 클래스/시퀀스 PlantUML | `docs/diagrams/aeb_class.puml`, `aeb_sequence_10ms.puml` | MBSE 리버스엔지니어링 데모 자산 |

## 3. 버림(捨) — 제외한 자료

| 원본 파일 | 판정 | 근거 |
|---|---|---|
| `TestingEmbeddedSoftware.doc` | **폐기** | Broekman & Notenboom의 2003년 저서에 대한 **서평(book review)** 문서. 세미나 주제와 무관 |
| `gemini-code-1787464853517.c` | **폐기** | 8줄짜리 As-Is/To-Be 단편. `agentic_analyzer.py`가 생성할 "AI 제안 코드" 예시 출력물일 뿐, 소스 자산이 아님 |
| `gemini-code-1787464860785.yaml` | **폐기** | `cicd-ct.yml`에 병합될 AI 트리거 스텝 단편. 별도 파일 유지 시 혼선 |
| ACC(`Acc_Core.c`) 상태머신 예제 | **폐기** | 대화 전반부의 1차 시도. 소스 자체가 없고, 데모에 AEB/ACC 두 소재를 넣으면 메시지가 흐려짐 |
| `*.mhtml` (11.4MB, 2개) | **로컬 보관 / 저장소 제외** | 원본 대화록. 아래 주의 사항 참조 |

> **`_archive/` 는 이 저장소에 커밋하지 않는다 (`.gitignore` 로 차단).**
> Gemini 페이지를 mhtml 로 저장하면 좌측 사이드바의 전체 대화 목록과 Google Drive 파일 목록까지
> 함께 캡처되어, 개인 메일주소·메일 백업 파일명·고객사 및 제안서 파일명·무관한 개인 대화 제목이
> 포함된다. 근거 보존이 필요하면 로컬에만 두고, 필요 없어지면 폴더째 삭제할 것.

---

## 4. 결함 리스트

### D-0 [Blocker] `Std_Types.h` 부재 → 빌드 불가
`Aeb_Interfaces.h:4` 가 `#include "Std_Types.h"` 하며 `float32`/`boolean`/`uint8`/`TRUE`/`FALSE`
를 사용하는데, 해당 헤더가 어디에도 없었다. **컴파일 자체가 안 됐다.**
→ 조치: AUTOSAR 스타일 최소 `Std_Types.h` 신규 작성.

### D-1 [Blocker] 단위시험 2건이 반드시 실패한다
`test_Aeb_FusionEngine.cpp` 의 테스트 1·2가
`EXPECT_CALL(mockCamera, GetCameraTarget(_)).WillOnce(Return());` 을 설정하지만,
`Aeb_FusionEngine.c` 는 `GetCameraTarget()` 을 **호출하지 않는다**
(대화 중간 "복원" 버전에는 있었으나 최종 저장 파일에서 누락).
→ gmock 미충족 기대치로 **테스트 2건 FAIL**.
→ 선택지: (A) 테스트에서 해당 EXPECT_CALL 제거, 또는 (B) 코드에 카메라 타겟 수집 추가.
   SRS-AEB-301이 "레이더와 **카메라**로부터 수집"을 요구하므로 **(B)가 정답**이며,
   이 자체가 "요구사항-코드 불일치를 AI가 잡아낸다"는 데모 소재가 된다.
→ **미수정 보존.** 증거: `docs/evidence/d1_camera_target_unused.txt`
   (컴파일러도 `unused variable 'cameraTarget'` 로 같은 것을 지적한다)

### D-2 [High] Epsilon 방어 로직이 도달 불가(dead code)
`Aeb_FusionEngine.c:30` 가드가 `RelativeSpeed_Kmph < -0.5F` 이므로,
`:34` 에 도달하는 시점의 `relSpeed_Mps` 는 항상 `0.5/3.6 = 0.139 m/s` 초과다.
따라서 `relSpeed_Mps > 0.01F` 는 **항상 참** → else 경로 실행 불가.
- 결과 1: **브랜치 커버리지 100% 달성 불가** (CT 데모에서 반드시 티가 난다)
- 결과 2: 테스트 3 `CalculateTTC_DivideByZero_Prevention` 은 `-0.001 km/h` 를 주입하는데
  이는 `-0.5` 가드에서 이미 걸러진다. 즉 **의도한 Epsilon 방어를 검증하지 않으면서 PASS** 하는
  가짜 테스트(false-positive test)다.
- 결과 3: MISRA Rule 14.3 (불변 조건) 위배 소지.
→ 조치 선택지: `-0.5 km/h` 가드와 Epsilon 중 하나로 통일하거나, `CalculateTTC()` 를 직접 호출하는
  화이트박스 테스트 추가.
→ **미수정 보존.** 실측 근거: `docs/evidence/d2_dead_branch_probe.txt` (경계 스윕 결과)

### D-3 [Blocker] `cicd-ct.yml` 이 존재하지 않는 것들을 참조
1. `Aeb_Interfaces.c` 컴파일 — **그런 파일 없다** (헤더 온리)
2. `libgmock-dev` 미설치 + `-lgmock` 링크 누락 → gmock 사용 테스트 링크 실패
3. `test_functional_scenario.py`, `scripts/upload_to_codebeamer.py` 경로 불일치
4. `actions/checkout@v3` → v4
5. 커버리지/업로드 스텝에 `if: always()` 없음 → **테스트 실패 시 리포트가 Codebeamer로 안 간다.**
   실패 케이스를 보여주는 게 데모의 핵심인데 실패하면 아무것도 올라가지 않는다.
6. `libaeb.so` 와 `unit_test` 가 **같은 디렉토리에서 `Aeb_FusionEngine.c` 를 두 번 계측 빌드** →
   `.gcda` 파일명 충돌로 카운터 오염(`profiling: cannot merge`). 빌드 디렉토리 분리 필요.

### D-4 [Blocker] SIL 기능시험 하네스가 존재하지 않는다
`test_functional_scenario.py` 가 호출하는 `Aeb_Init_Wrapper()`, `SetMockRadarTarget()`,
`Aeb_MainFunction_10ms_Wrapper()`, `GetBrakeCommand()` 는 **어디에도 구현이 없었다.**
추가로 ctypes 기본 `restype` 은 `int` 라서 `GetBrakeCommand() == 100.0` 비교는
`restype = c_float` 를 지정하지 않으면 쓰레기값이 나온다.
→ 조치: `test/Aeb_TestHarness.c` 신규 작성 (Mock 센서/액추에이터 + C 래퍼 export).
   시나리오 수치도 검증됨: 30m/-60km/h → TTC 1.8s, 20m/-60km/h → 1.2s.

### D-5 [High] Codebeamer Test Run API 엔드포인트가 틀렸다
`upload_to_codebeamer.py` 는 `POST /api/v3/trackers/{id}/items` 로 Test Run을 만들려 했다.
Codebeamer v3 는 테스트 실행 전용 엔드포인트가 따로 있다:
- `POST /api/v3/trackers/{testRunTrackerId}/testruns`
- `POST /api/v3/trackers/{testRunTrackerId}/automatedtestruns` ← **CI 자동화 결과용. 이게 정답.**

추가 문제:
- `response.json()["id"]` — 상태코드 확인 없음. 실패 시 KeyError로 파이프라인이 엉뚱하게 죽는다.
- **Test Case 항목과 링크하지 않는다.** Test Run만 만들면 추적성이 안 생겨 데모의 목적 자체가 무너진다.
- 커버리지 파일은 인자로 받기만 하고 **업로드하지 않는다**.
- 트래커 ID `12345` 하드코딩, timeout/verify 미지정.

### D-6 [High] `agentic_analyzer.py` 가 인자를 무시하고, MCP도 아니다
- `cicd-ct.yml` 은 `--test-report`, `--source-dir`, `--issue-id` 를 넘기지만
  스크립트에 **argparse가 없어 전부 무시**되고 `unit_report.xml` / 이슈 `10254` 를 하드코딩했다.
- 코멘트 payload `{"format": "Markdown"}` — Codebeamer는 `commentFormat` 필드에
  `Html`/`Wiki`/`PlainText` 를 받는다. `Markdown` 은 유효값이 아니다.
- 스스로를 "MCP 기반 에이전트"라 설명하면서 실제로는 `requests.post` 로 OpenAI를 직접 호출했다.
  **MCP 요소가 전혀 없었다.** 모델도 `gpt-4-turbo` 하드코딩.
- HTTP 오류 처리 전무.

---

## 5. 전략 갭

### G-1 [Critical] "Codebeamer → CI 트리거" 문제가 미해결
원래 질문은 *"Codebeamer에 GitHub trigger가 없어서 Jenkins를 생각 중"* 이었다.
Gemini 답변은 **CI → Codebeamer (결과 리포팅)** 방향만 해결하고,
**Codebeamer → CI (실행 촉발)** 방향은 다루지 않은 채 "Jenkins 완전 대체"라고 선언했다.
`on: push` 뿐이면 Codebeamer에서 요구사항이 승인되거나 Test Set이 실행 요청될 때 파이프라인이 돌지 않는다.
→ 조치: Codebeamer 워크플로우 액션에서 `POST /repos/{owner}/{repo}/dispatches`
  (`repository_dispatch`) 를 호출하는 구성 (`scripts/cb_trigger_ci.py`).
  플러그인 개발 없이 해결 가능하며, **"Jenkins를 걷어낸다"는 주장의 유일한 증명 수단**이다.

### G-2 커버리지 임계 게이트가 없다
파이프라인/시퀀스 다이어그램에는 "Coverage < 80%" 조건이 등장하지만
실제 yml에는 임계 검사가 없었다. `gcovr --fail-under-line 80 --fail-under-branch 70` 추가.
(D-2로 인해 브랜치 100%는 애초에 불가하므로 임계값 설정 시 유의)

### G-3 AI 연계 시나리오가 1개뿐 (실패 분석)
세미나 주제가 "AI RM DevOps"인데 AI 활용이 "테스트 실패 원인 분석 코멘트" 하나였다.
현재 자료에서 곧바로 파생 가능한 시나리오:
1. 요구사항 → 테스트케이스 자동 생성 (SRS-AEB-xxx 기반 gtest 초안)
2. 코드 → 요구사항 역산 및 **미추적 코드/고아 테스트 검출** (D-1, SRS-205/206 사례 실물 보유)
3. 커버리지 미달 구간에 대한 추가 테스트케이스 제안 (D-2 도달 불가 코드 사례 실물 보유)
4. MISRA 위배 사항 → Codebeamer 결함 항목 자동 등록
→ **1~4 모두 이번 검토에서 실제 결함으로 발견된 것들이라, "AI가 찾았다"는 서사를 조작 없이 시연 가능하다.**

### G-4 Codebeamer MCP 서버 활용 미반영
Codebeamer MCP 서버가 이미 존재한다(`cb_create_item`,
`cb_post_trackers_by_test_run_tracker_id_automatedtestruns`, `cb_tca_coverage_report` 등).
`requests`로 REST를 직접 때리는 방식보다
**"LLM이 MCP 도구로 ALM을 직접 조작한다"** 가 세미나 메시지에 훨씬 부합하고 시연 임팩트도 크다.
→ REST 스크립트(파이프라인 자동화용)와 MCP(대화형 시연용)를 **역할 분담**하는 구성 채택.

---

## 6. 조치 결과 (2026-08-23)

| ID | 조치 | 상태 |
|---|---|---|
| D-0 | `src/Std_Types.h` 신규 작성 (AUTOSAR 타입 최소 정의) | ✅ **빌드 성공 실측 확인** |
| D-1 | **미수정 — 데모 소재로 의도적 보존** | 근거: `docs/evidence/d1_camera_target_unused.txt` |
| D-2 | **미수정 — 데모 소재로 의도적 보존** | 근거: `docs/evidence/d2_dead_branch_probe.txt` (실측 스윕) |
| D-3 | `ci/cicd-ct.yml` 전면 재작성 | ✅ YAML 문법 검증 완료 |
| D-4 | `test/Aeb_TestHarness.c` 신규 + 기능시험 재작성 | ✅ **SIL 6건 전부 통과 실측 확인** |
| D-5 | `automatedtestruns` 엔드포인트로 교체, 오류처리/첨부/Test Case 링크 추가 | ⚠️ dry-run 검증 완료 / **서버 스키마 대조 미완** |
| D-6 | argparse·`commentFormat` 수정, Claude Opus 5 + 구조화 출력으로 재작성 | ✅ dry-run 검증 완료 |
| G-1 | `scripts/cb_trigger_ci.py` 신규 + `repository_dispatch` 트리거 | ✅ dry-run 검증 완료 / 워크플로우 배선 미완 |
| G-2 | `gcovr --fail-under-line/--fail-under-branch` 게이트 추가 | ✅ 완료 |
| G-3 | AI 시나리오를 실패분석 + 요구사항 불일치 + 커버리지 갭 3종으로 확장 | ✅ 데모 시나리오 반영 |
| G-4 | REST(파이프라인) / MCP(대화형) 역할 분담 구조 채택 | ✅ 아키텍처 반영 / 시연 스크립트 미완 |

### D-3 세부 조치
1. 없는 `Aeb_Interfaces.c` 컴파일 제거, `test/Aeb_TestHarness.c` 로 대체
2. `libgmock-dev` 설치 및 `-lgmock` 링크 추가
3. 재배치된 경로(`src/`, `test/`, `scripts/`)에 맞게 수정
4. `actions/checkout@v4`, `upload-artifact@v4`
5. 시험 스텝을 `continue-on-error` 로 전환 + 커버리지/업로드에 `if: always()`
   → **실패해도 증적이 Codebeamer 로 올라간다.** 최종 판정은 마지막 게이트가 담당.
6. `build/unit`, `build/sil` 분리로 `.gcda` 충돌 해소
7. Codebeamer 항목 ID 결정 로직 추가 (dispatch payload → workflow input → 커밋 메시지 파싱)

### 실측 검증 환경
- 컴파일: `gcc 6.3 (MinGW, 32bit)` / `x86_64-pc-cygwin-gcc 14`
- 기능시험: Python 3.14 + pytest, ctypes 로 공유 라이브러리 로드
- 검증 못 한 것: GTest/GMock 단위 시험(로컬에 gtest 미설치), Codebeamer 실 서버 연동(HTTP 500)
