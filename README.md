# AEB PoC — AI RM DevOps: CI/CD/CT 연계 데모 프로젝트

Codebeamer 기반 ALM 에서 **요구사항 → 설계 → 구현 → 단위/기능 시험 → 커버리지 → 컴플라이언스**
전 과정을 AI 로 연계하는 세미나 데모용 샘플 프로젝트.

- 소재: AEB(Autonomous Emergency Braking) 센서 퓨전 엔진, C / ASPICE V-모델
- 데모 진행 순서 및 발표 멘트: [docs/DEMO_SCENARIO.md](docs/DEMO_SCENARIO.md)
- 이 저장소가 만들어진 판단 근거: [REVIEW.md](REVIEW.md)

## 현재 상태

| 구분 | 상태 |
|---|---|
| C 코드 빌드 | ✅ 검증 완료 (`Std_Types.h` 신규 작성) |
| 기능 시험(SIL) | ✅ **6건 전부 통과 실측 확인** (하네스 신규 작성) |
| 단위 시험(GTest) | ⚠️ 2건 실패 — **의도적 보존** (요구사항-코드 불일치 데모 소재) |
| 커버리지 게이트 | ⚠️ 브랜치 100% 불가 — **의도적 보존** (도달 불가 코드 데모 소재) |
| CI 파이프라인 | ✅ 재작성 완료 (YAML 검증, 트리거 4종), `.github/workflows/` 배치 완료 |
| Codebeamer 업로드 | ⚠️ 스크립트 재작성 완료 / **서버 스키마 실측 대조 미완** |
| AI 실패 분석 | ✅ 재작성 완료 (Claude Opus 5 + 구조화 출력, dry-run 검증) |
| Codebeamer → CI 트리거 | ✅ 신규 작성 (`repository_dispatch`) |

> **의도적 실패 2건.** 단위 시험 2건 실패와 브랜치 커버리지 미달은 버그가 아니라 데모 자산이다.
> Gemini 원본 자료에 실제로 있던 결함이며, AI 가 요구사항-코드 불일치와 도달 불가 방어 코드를
> 찾아내는 과정을 조작 없이 시연하기 위해 남겨두었다. 근거는 `docs/evidence/` 에 있다.

## 폴더 구조

```
.
├── README.md                          현재 문서
├── REVIEW.md                          Gemini 자료 검토 결과 (취/버림 + 결함 + 갭)
├── .github/workflows/
│   └── cicd-ct.yml                    GitHub Actions 파이프라인 (트리거 4종)
├── docs/
│   ├── DEMO_SCENARIO.md               세미나 진행 시나리오 (발표 멘트 포함)
│   ├── SRS_AEB_Requirements.md        SWE.1 요구사항 명세 (승인 15건 + 제안 3건)
│   ├── SRS_AEB_Requirements.csv       └ Codebeamer 임포트용 (UTF-8 BOM)
│   ├── SDD_AEB_Design.md              SWE.3 상세 설계 (Data Dictionary / IF / 페일세이프 / MISRA)
│   ├── Traceability_Matrix.csv        SRS ↔ 코드 라인 ↔ 테스트 ↔ 커버리지
│   ├── diagrams/
│   │   ├── aeb_class.puml             클래스 다이어그램 (정적 구조)
│   │   ├── aeb_sequence_10ms.puml     10ms 태스크 시퀀스 (동적 행위)
│   │   ├── agentic_pipeline.puml      AI 실패분석 파이프라인 시퀀스
│   │   └── cicd_ct_architecture.puml  CI/CD/CT 양방향 연계 (Jenkins 제거)
│   └── evidence/                      결함 실측 근거 (발표 백업 자료)
│       ├── d1_camera_target_unused.txt    요구사항-코드 불일치 컴파일러 증거
│       ├── d2_dead_branch_probe.txt       도달 불가 코드 스윕 결과
│       └── d2_dead_branch_probe.py        └ 재현 스크립트
├── src/
│   ├── Std_Types.h                    AUTOSAR 타입 최소 정의 (호스트 빌드용)
│   ├── Aeb_Interfaces.h               함수 포인터 기반 센서/액추에이터 인터페이스
│   └── Aeb_FusionEngine.c             TTC 계산 및 제동 판단 (MISRA 방어 로직)
├── test/
│   ├── test_Aeb_FusionEngine.cpp      단위시험 (GTest/GMock, 4 케이스)
│   ├── Aeb_TestHarness.c              SIL 하네스 (Mock 센서 + ctypes 노출 래퍼)
│   └── test_functional_scenario.py    기능시험 시계열 시나리오 (6 케이스)
└── scripts/
    ├── cb_trigger_ci.py               Codebeamer → GitHub repository_dispatch 트리거
    ├── upload_to_codebeamer.py        Test Run / 커버리지 결과 전송
    └── agentic_analyzer.py            실패 분석 (Claude) → Codebeamer 코멘트
```

### 정리 대상 임시 파일

초기 푸시 과정에서 생긴 잔여 파일 2개다. 내용은 비워 두었으니 지우면 된다.

```bash
git rm ci/cicd-ct.yml .github/PERMISSION_TEST.md
git commit -m "chore: 이동 완료된 임시 파일 제거"
git push
```

## 로컬 실행

기능 시험(SIL) — GTest 없이도 돌아간다:

```bash
mkdir -p build/sil
gcc --coverage -fPIC -Isrc -c src/Aeb_FusionEngine.c -o build/sil/Aeb_FusionEngine.o
gcc --coverage -fPIC -Isrc -c test/Aeb_TestHarness.c -o build/sil/Aeb_TestHarness.o
gcc --coverage -shared -o libaeb.so build/sil/*.o
AEB_LIB_PATH=./libaeb.so pytest test/test_functional_scenario.py -v
```

단위 시험 (GTest/GMock 필요):

```bash
mkdir -p build/unit
gcc --coverage -Isrc -c src/Aeb_FusionEngine.c -o build/unit/Aeb_FusionEngine.o
g++ --coverage -Isrc -c test/test_Aeb_FusionEngine.cpp -o build/unit/test_Aeb_FusionEngine.o
g++ --coverage -o unit_test build/unit/*.o -lgtest -lgtest_main -lgmock -pthread && ./unit_test
```

커버리지 병합:

```bash
gcovr -r . --filter 'src/.*' --xml-pretty -o coverage_report.xml --txt
```

Codebeamer 전송 페이로드를 서버 없이 확인:

```bash
python3 scripts/upload_to_codebeamer.py --dry-run --unit-report unit_report.xml --coverage coverage_report.xml
```

도달 불가 코드 실측 재현:

```bash
AEB_LIB_PATH=./libaeb.so python3 docs/evidence/d2_dead_branch_probe.py
```

## 필요한 Secrets

| 위치 | 키 | 용도 |
|---|---|---|
| GitHub | `CB_URL` | Codebeamer 베이스 URL |
| GitHub | `CB_TOKEN` | Codebeamer PAT (Basic 인증 대신 권장) |
| GitHub | `CB_TEST_RUN_TRACKER_ID` | Test Run 트래커 ID |
| GitHub | `CB_TEST_CASE_TRACKER_ID` | Test Case 트래커 ID (추적성 링크용) |
| GitHub | `ANTHROPIC_API_KEY` | AI 실패 분석 |
| Codebeamer | `GITHUB_REPOSITORY`, `GITHUB_PAT` | CI 트리거 (repository_dispatch) |

## 남은 작업

1. **Codebeamer `automatedtestruns` 스키마 대조** — 대상 서버가 전 요청에 HTTP 500 응답 중이라 실측 검증 보류. 서버 복구 후 `--dry-run` 출력과 swagger 스키마 대조 필요.
2. **Codebeamer 트래커 구성** — Requirements / Test Case / Test Run / Bug 4종 생성 및 SRS CSV 임포트, ASIL·Verification Method 커스텀 필드 추가.
3. **Codebeamer 워크플로우 액션 배선** — `cb_trigger_ci.py` 를 전환 액션에 연결 (스크립트 실행 권한 확인 필요).
4. **Codebeamer MCP 대화형 시연 스크립트** — 질의 3~4개 확정 및 리허설.
5. GTest/GMock 환경에서 단위 시험 실패 2건 재현 확인 (현재는 컴파일러 경고로만 확인).
6. 임시 파일 2개 삭제 (위 "정리 대상 임시 파일" 참조).
