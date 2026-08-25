# AEB PoC — AI RM DevOps: CI/CD/CT 연계 데모 프로젝트

Codebeamer 기반 ALM 에서 **요구사항 → 설계 → 구현 → 단위/기능 시험 → 커버리지 → 컴플라이언스**
전 과정을 AI 로 연계하는 세미나 데모용 샘플 프로젝트.

- 소재: AEB(Autonomous Emergency Braking) 센서 퓨전 엔진, C / ASPICE V-모델
- **개발 정리 (발표용)**: [docs/ENGINEERING_SUMMARY.md](docs/ENGINEERING_SUMMARY.md)
- 데모 진행 순서: [docs/DEMO_SCENARIO.md](docs/DEMO_SCENARIO.md)
- 기존 자료 검토 결과: [REVIEW.md](REVIEW.md)
- 인수인계: [docs/HANDOFF.md](docs/HANDOFF.md)

## 현재 상태

| 구분 | 상태 |
|---|---|
| C 코드 빌드 | ✅ 검증 완료 (`Std_Types.h` 신규 작성) |
| 기능 시험(SIL) | ✅ **6건 전부 통과** — 로컬·CI 양쪽 실측 |
| 단위 시험(GTest) | ⚠️ 2건 실패 — **의도적 보존**. CI 실환경에서 재현 확인 |
| 커버리지 | ✅ 라인 **100.00%** (44/44) / ⚠️ 브랜치 **63.89%** (23/36) |
| 커버리지 게이트 | ✅ 동작 확인 (`gcovr` exit 4, 브랜치 임계 미달) |
| CI 파이프라인 | ✅ **실행 확인** (run 32654599107) |
| 추적성 Pages | ✅ 배포 후 200, 링크 대상 라인 범위 정확 |
| Codebeamer 스키마 대조 | ✅ 완료 — 필드 매핑 오류 2건 발견·수정 |
| Codebeamer 요구사항 적재 | ✅ **21건 적재 + 필드 정규화 완료** |
| Codebeamer Test Run 생성 | ⚠️ Secrets 미설정 / 요청 봉투 스키마 미검증 |
| AI 실패 분석 | ⚠️ dry-run 검증 완료 / 실행은 API 키 미설정 |
| Codebeamer → CI 트리거 | ⚠️ 스크립트 완료 / 워크플로 액션 배선 미완 |
| codebeamer-mcp 개선 | ⚠️ 로컬 검증 완료 / **MCP 재시작 후 실서버 확인 필요** |

브랜치 63.89% 는 미달이 아니라 **설명된 미달**이다. 미실행 분기 13개가 전부
3개 요구사항으로 분해된다 — 상세는 [docs/CI_VERIFICATION_LOG.md](docs/CI_VERIFICATION_LOG.md) 3절.

## 폴더 구조

```
ptc_cicdct/
├── README.md                          현재 문서
├── REVIEW.md                          기존 Gemini 자료 검토 (취/버림 + 결함 + 갭)
├── Doxyfile                           @req/@verifies 를 xrefitem 으로 매핑
├── .gitignore
├── .github/workflows/
│   ├── cicd-ct.yml                    빌드→단위→SIL→커버리지→ALM→판정 게이트
│   └── pages.yml                      Doxygen→심볼 인덱스→리다이렉트→Pages 배포
├── docs/
│   ├── ENGINEERING_SUMMARY.md         ★ 개발 정리 — 산출물 + 기술 고려사항 10건 + 수치
│   ├── DEMO_SCENARIO.md               세미나 진행 시나리오 (말할 것 포함)
│   ├── CI_VERIFICATION_LOG.md         CI 실행으로 확인된 사실 + 실측 수치
│   ├── TRACEABILITY_LINKING.md        안 끊어지는 코드 링크 설계
│   ├── HANDOFF.md                     인수인계 (공개용 판본)
│   ├── SRS_AEB_Requirements.md        SWE.1 요구사항 명세 (승인 15건 + 제안 3건)
│   ├── SRS_AEB_Requirements.csv       └ Codebeamer 임포트용 (UTF-8 BOM)
│   ├── SDD_AEB_Design.md              SWE.3 상세 설계 (Data Dictionary / IF / MISRA)
│   ├── Traceability_Matrix.csv        SRS ↔ 코드 라인 ↔ 테스트 ↔ 커버리지
│   ├── generated/CODE_INDEX.md        자동 생성 코드 인덱스
│   ├── diagrams/                      PlantUML 4종 (클래스/시퀀스/AI 파이프라인/아키텍처)
│   └── evidence/                      결함 실측 근거 (발표 백업 자료)
│       ├── d1_camera_target_unused.txt    요구사항-코드 불일치 컴파일러 증거
│       ├── d2_dead_branch_probe.txt/.py   도달 불가 코드 실측 스윕 + 재현 스크립트
│       └── coverage_branch_analysis.txt   미실행 분기 13개 분해
├── src/
│   ├── Std_Types.h                    AUTOSAR 타입 최소 정의 (호스트 빌드용)
│   ├── Aeb_Interfaces.h               함수 포인터 기반 센서/액추에이터 인터페이스
│   └── Aeb_FusionEngine.c             TTC 계산 및 제동 판단 (MISRA 방어 로직)
├── test/
│   ├── test_Aeb_FusionEngine.cpp      단위시험 (GTest/GMock, 4 케이스)
│   ├── Aeb_TestHarness.c              SIL 하네스 (Mock 센서 + ctypes 노출 래퍼)
│   └── test_functional_scenario.py    기능시험 시계열 시나리오 (6 케이스)
└── scripts/
    ├── build_symbol_map.py            ctags 심볼 인덱싱 (정규식 폴백 포함)
    ├── generate_redirects.py          sym/ req/ 리다이렉트 페이지 생성
    ├── cb_trigger_ci.py               Codebeamer → GitHub repository_dispatch
    ├── upload_to_codebeamer.py        시험 결과/커버리지 전송 (--check-schema)
    ├── agentic_analyzer.py            실패 분석 (Claude Opus 5) → ALM 코멘트
    └── seed_codebeamer_demo.py        데모 데이터 시더 (dry-run 우선)
```

> `_archive/` (Gemini 원본 대화록) 는 개인정보·고객사명이 섞여 있어
> `.gitignore` 로 **영구 제외**했다. 새 PC 로 옮길 때도 가져가지 말 것.

## 저장소 밖에 있는 것 ★

**codebeamer-mcp 개선분**은 이 저장소에 없다. `C:\cb\codebeamer-mcp-dist` 에 있고
아직 git 저장소가 아니다. 버그 3건 수정 + 도구 3종 추가(CSV 라운드트립 포함).
상세는 그 폴더의 `CHANGELOG_20260825.md`, 옮기는 방법은 [docs/HANDOFF.md](docs/HANDOFF.md) 2절.

## 로컬 실행

```bash
mkdir -p build/unit build/sil
gcc --coverage -fPIC -Isrc -c src/Aeb_FusionEngine.c -o build/sil/Aeb_FusionEngine.o
gcc --coverage -fPIC -Isrc -c test/Aeb_TestHarness.c -o build/sil/Aeb_TestHarness.o
gcc --coverage -shared -o libaeb.so build/sil/*.o
AEB_LIB_PATH=./libaeb.so pytest test/test_functional_scenario.py -v
```

단위 시험 빌드 (GTest/GMock 필요). `build/unit` 과 `build/sil` 을 **반드시 분리**한다 —
같은 오브젝트를 두 번 계측하면 `.gcda` 가 충돌한다.

```bash
gcc --coverage -Isrc -c src/Aeb_FusionEngine.c -o build/unit/Aeb_FusionEngine.o
g++ --coverage -Isrc -c test/test_Aeb_FusionEngine.cpp -o build/unit/test_Aeb_FusionEngine.o
g++ --coverage -o unit_test build/unit/*.o -lgtest -lgtest_main -lgmock -pthread && ./unit_test
```

Codebeamer 전송을 서버 없이 확인:

```bash
python3 scripts/upload_to_codebeamer.py --dry-run --unit-report unit_report.xml --coverage coverage_report.xml
```

실 서버 스키마와 대조 (전송 없음):

```bash
python3 scripts/upload_to_codebeamer.py --check-schema
```

## 필요한 Secrets

| 위치 | 키 | 용도 |
|---|---|---|
| GitHub | `CB_URL` | Codebeamer 베이스 URL |
| GitHub | `CB_TOKEN` | Codebeamer PAT (Basic 인증 대신 권장) |
| GitHub | `CB_TEST_RUN_TRACKER_ID` | Test Run 트래커 ID |
| GitHub | `CB_TEST_CASE_TRACKER_ID` | Test Case 트래커 ID — **선택이 아니라 필수** (`testCases` 가 필수 필드) |
| GitHub | `ANTHROPIC_API_KEY` | AI 실패 분석 |
| Codebeamer | `GITHUB_REPOSITORY`, `GITHUB_PAT` | CI 트리거 (repository_dispatch) |

## 남은 작업

우선순위 순. 전체 맥락은 [docs/HANDOFF.md](docs/HANDOFF.md) 4절.

1. **codebeamer-mcp 를 저장소로** — 현재 로컬 디스크에만 있다
2. **MCP 재시작 후 실서버 검증** — 신규 도구 3종은 로컬 검증만 마쳤다
3. **SDD 적재 + association 연결** — 요구사항 ↔ 코드/설계를
   `is related to` / `is derived from` 으로. 아직 시작 안 함
4. **Test Case 트래커 필드 정규화** — description 에 코드 링크·메타데이터가 남아 있다
5. **Secrets 설정** — 위 표. 미설정이라 Test Run 생성과 AI 분석이 실행되지 않는다
6. **Codebeamer 워크플로 액션 배선** — `cb_trigger_ci.py` 를 전환 액션에 연결
7. **`automatedtestruns` 요청 봉투 스키마 대조** — 필드명은 확정, 봉투는 문서 기준 추정
8. **정리** — `ci/cicd-ct.yml`, `.github/PERMISSION_TEST.md` 잔재 삭제.
   `upload_to_codebeamer.py` / `agentic_analyzer.py` 의 `Html` → `Wiki` 수정
