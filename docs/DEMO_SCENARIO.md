# 세미나 데모 시나리오 — AI 도입을 통한 CI/CD/CT 연계

- 대상: AI RM DevOps 세미나 / Codebeamer 기반 ALM 통합 관리
- 소재: AEB(긴급 제동 보조) 센서 퓨전 엔진
- 소요: 약 15분 (라이브 12분 + 질의 3분)

## 핵심 메시지 3줄

1. **Jenkins 없이도 ALM 이 CI 를 촉발하고, CI 가 ALM 에 증적을 되돌린다** — 양방향 연계는 플러그인 개발 없이 REST API 두 개로 성립한다.
2. **단위 시험만이 아니라 기능 시험(SIL)까지 커버리지 계측 하에 자동 수행된다** — 하드웨어 없이 시계열 주행 시나리오를 검증한다.
3. **AI 는 "실패 로그 요약기"가 아니다** — 요구사항과 코드의 불일치, 가짜 통과 테스트, 도달 불가 방어 코드를 찾아내 ALM 항목으로 되돌린다.

---

## 데모 흐름

### [0] 사전 세팅 (화면 미노출)
| 항목 | 값 |
|---|---|
| Codebeamer | Requirements / Test Case / Test Run / Bug 트래커 4종 |
| 요구사항 임포트 | `docs/SRS_AEB_Requirements.csv` (승인 15건) |
| GitHub Secrets | `CB_URL`, `CB_TOKEN`, `CB_TEST_RUN_TRACKER_ID`, `CB_TEST_CASE_TRACKER_ID`, `ANTHROPIC_API_KEY` |
| Codebeamer Secrets | `GITHUB_REPOSITORY`, `GITHUB_PAT` |
| 워크플로 배치 | `ci/cicd-ct.yml` → `.github/workflows/cicd-ct.yml` 로 이동 |

### [1] 요구사항에서 출발 (2분)
Codebeamer Requirements 트래커에서 `SRS-AEB-305`(보행자 가중치 0.8)와 `SRS-AEB-401`(TTC 1.5초 미만 제동)을 보여준다.

> **말할 것:** "이 두 요구사항은 따로 보면 평범하지만, 곱해지면 제동 판단이 역전됩니다. 18m / -36km/h 는 TTC 1.8초로 제동하지 않는데, 보행자가 감지되면 1.44초가 되어 제동합니다. 이 상호작용을 검증하는 게 SWE.4 의 본질입니다."

`docs/Traceability_Matrix.csv` 로 요구사항 → 코드 라인 → 테스트 케이스 연결을 보여준다.

### [2] ALM 이 CI 를 촉발 (2분) — **G-1, 차별화 지점**
Codebeamer Test Set 에서 "실행 요청" 워크플로우 전환을 실행한다.
→ 워크플로우 액션이 `scripts/cb_trigger_ci.py` 호출
→ GitHub Actions 가 `repository_dispatch` 로 기동

> **말할 것:** "보통 여기서 Jenkins 가 등장합니다. Codebeamer 에 GitHub 트리거가 없으니까요. 그런데 실제로 필요한 건 REST 호출 한 번입니다. 플러그인 개발도, Jenkins 유지보수도 필요 없습니다."

### [3] 파이프라인 자동 실행 (3분)
Actions 로그를 따라가며 5단계를 보여준다.

| 단계 | 보여줄 것 |
|---|---|
| 계측 빌드 | `gcc --coverage`, 빌드 디렉토리 분리(`build/unit`, `build/sil`) |
| 단위 시험 | GTest/GMock 으로 C 함수 포인터 인터페이스를 목 주입 |
| **기능 시험(SIL)** | pytest + ctypes 로 C 라이브러리를 로드해 **10ms 태스크를 시간 순서대로 반복 호출** |
| 커버리지 | gcovr 로 단위+기능 커버리지를 소스 기준 병합 |
| ALM 리포팅 | Codebeamer Test Run 자동 생성 + Test Case 링크 + 커버리지 첨부 |

> **말할 것:** "기능 시험이 단위 시험과 다른 점은 시간입니다. 30m 에서 20m 로 접근하는 20 사이클을 돌려 제동이 정확히 어느 시점에 걸리는지 봅니다. 하드웨어는 없습니다."

### [4] 실패가 발생한다 (3분) — **하이라이트**
단위 시험 2건이 실패한다. AI 에이전트 스텝이 자동 기동한다.

Codebeamer Bug 항목에 붙은 AI 코멘트를 보여준다:

| 필드 | 예상 내용 |
|---|---|
| 결함 유형 | **요구사항-코드 불일치** (`requirement_mismatch`) |
| 근본 원인 | 테스트는 `GetCameraTarget()` 호출을 기대하지만 `Aeb_FusionEngine.c` 는 호출하지 않음 |
| 관련 요구사항 | `SRS-AEB-301` ("레이더와 **카메라**로부터 타겟 데이터를 수집해야 한다") |
| 권고 조치 | 코드 수정 (테스트가 아니라 코드가 요구사항에 미달) |

> **말할 것:** "AI 가 한 판단의 핵심은 '테스트를 고칠 것인가, 코드를 고칠 것인가'입니다. 요구사항 301번이 카메라 수집을 요구하고 있으니 코드가 틀린 겁니다. 이게 요구사항이 ALM 에 있어야 AI 가 제대로 판단할 수 있는 이유입니다."

**보강 증거:** 컴파일러도 같은 것을 봤다 — `warning: unused variable 'cameraTarget'`
(`docs/evidence/d1_camera_target_unused.txt`)

### [5] 커버리지가 100% 가 안 된다 (2분) — **두 번째 하이라이트**
브랜치 커버리지 게이트 미달을 보여주고, AI 분석 결과를 보여준다.

> **말할 것:** "Epsilon 방어 코드는 0으로 나누기를 막기 위해 넣은 것입니다. 그런데 상위 가드가 상대속도 -0.5km/h 미만만 통과시키므로, 이 지점의 분모는 항상 0.139 m/s 이상입니다. Epsilon 임계값의 14배입니다. 즉 **이 방어 코드는 절대 실행되지 않습니다.**"

이어서: "더 나쁜 건 이걸 검증한다고 쓴 테스트가 통과한다는 겁니다. -0.001km/h 를 넣었는데 상위 가드에서 이미 걸러지죠. **의도한 로직을 건드리지도 않고 초록불이 켜집니다.** 커버리지 숫자만 보면 못 찾고, AI 는 가드 조건을 함께 읽어야 찾습니다."

실측 근거는 `docs/evidence/d2_dead_branch_probe.txt` 참조.
현장에서 직접 돌려도 된다:

```
AEB_LIB_PATH=./libaeb.so python3 docs/evidence/d2_dead_branch_probe.py
```

### [6] 대화형 마무리 (2분) — Codebeamer MCP
Claude 에서 MCP 로 Codebeamer 를 직접 조회한다.

- "AEB 프로젝트에서 테스트가 연결되지 않은 요구사항 보여줘"
- "이번 빌드의 Test Run 결과를 요구사항별로 정리해줘"

> **말할 것:** "파이프라인 자동화는 REST 로 합니다. 사람이 묻는 건 MCP 로 합니다. 자동화와 대화, 두 경로가 같은 ALM 데이터를 씁니다."

---

## 실패를 의도적으로 남긴 이유

D-1(요구사항-코드 불일치)과 D-2(도달 불가 방어 코드)는 **고치지 않고 남겨두었다.**
Gemini 가 만든 원본 자료에 실제로 들어 있던 결함이며, 조작 없이 AI 의 발견 능력을 시연할 수 있는 소재다.

빌드/실행을 막던 결함(`Std_Types.h` 부재, SIL 하네스 부재, 파이프라인 참조 오류)만 수정했다.
자세한 판정은 [REVIEW.md](../REVIEW.md) 참조.

## 시연 리스크 및 대비

| 리스크 | 대비 |
|---|---|
| Codebeamer 서버 응답 불안정 (2026-08-23 시점 HTTP 500 관측) | 사전에 `--dry-run` 으로 페이로드 검증, 실패 시 녹화 영상 대체 |
| `automatedtestruns` 스키마 인스턴스 차이 | 데모 전 `--dry-run` 출력과 서버 swagger 스키마 대조 필수 |
| Claude API 지연 | 사전 1회 실행하여 결과를 캐시, 라이브에서는 이미 달린 코멘트를 보여주는 순서로 전환 |
| GitHub Actions 큐 지연 | `workflow_dispatch` 로 사전 워밍업 1회 실행 |
| 워크플로 파일 미이동 | `ci/cicd-ct.yml` 이 `.github/workflows/` 에 있는지 데모 전 확인 |
