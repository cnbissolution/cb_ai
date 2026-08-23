# AEB PoC — AI RM DevOps: CI/CD/CT 연계 데모 프로젝트

Codebeamer 기반 ALM 에서 **요구사항 → 설계 → 구현 → 단위/기능 시험 → 커버리지 → 컴플라이언스**
전 과정을 AI 로 연계하는 세미나 데모용 샘플 프로젝트.

- 소재: AEB(Autonomous Emergency Braking) 센서 퓨전 엔진, C / ASPICE V-모델
- 데모 진행 순서 및 발표 멘트: [docs/DEMO_SCENARIO.md](docs/DEMO_SCENARIO.md)
- 추적성 링크 체계: [docs/TRACEABILITY_LINKING.md](docs/TRACEABILITY_LINKING.md)
- 이 저장소가 만들어진 판단 근거: [REVIEW.md](REVIEW.md)

## 현재 상태

| 구분 | 상태 |
|---|---|
| C 코드 빌드 | ✅ 검증 완료 (`Std_Types.h` 신규 작성) |
| 기능 시험(SIL) | ✅ **6건 전부 통과 실측 확인** (하네스 신규 작성) |
| 단위 시험(GTest) | ⚠️ 2건 실패 — **의도적 보존** (요구사항-코드 불일치 데모 소재) |
| 커버리지 게이트 | ⚠️ 브랜치 100% 불가 — **의도적 보존** (도달 불가 코드 데모 소재) |
| CI 파이프라인 | ✅ 재작성 완료 (YAML 검증, 트리거 4종), `.github/workflows/` 배치 완료 |
| 코드 인덱스 / 안정 링크 | ✅ 스크립트 검증 완료 (심볼 31개, 요구사항 17건) / **Pages 활성화 필요** |
| Codebeamer 업로드 | ⚠️ 스크립트 재작성 완료 / **서버 스키마 실측 대조 미완** |
| AI 실패 분석 | ✅ 재작성 완료 (Claude Opus 5 + 구조화 출력, dry-run 검증) |
| Codebeamer → CI 트리거 | ✅ 신규 작성 (`repository_dispatch`) |

> **의도적 실패 2건.** 단위 시험 2건 실패와 브랜치 커버리지 미달은 버그가 아니라 데모 자산이다.
> Gemini 원본 자료에 실제로 있던 결함이며, AI 가 요구사항-코드 불일치와 도달 불가 방어 코드를
> 찾아내는 과정을 조작 없이 시연하기 위해 남겨두었다. 근거는 `docs/evidence/` 에 있다.

## 추적성 링크 (핵심 자산)

ALM 에는 **심볼 이름 기준의 안정적인 URL** 을 저장한다. 라인 번호는 CI 가 매번 재계산한다.

```
https://cnbissolution.github.io/cb_ai/req/SRS-AEB-305/        요구사항 -> 구현·검증 위치
https://cnbissolution.github.io/cb_ai/sym/src/Aeb_FusionEngine.c/CalculateTTC/   심볼 -> 코드
```

`src/` 의 `@req` 와 `test/` 의 `@verifies` 주석을 CI 가 파싱해 인덱스를 만들고,
구현과 검증이 한쪽만 있는 요구사항을 **추적성 갭으로 자동 노출**한다 (현재 5건).
자세한 내용은 [docs/TRACEABILITY_LINKING.md](docs/TRACEABILITY_LINKING.md) 참조.

## 폴더 구조

```
.
├── README.md                          현재 문서
├── REVIEW.md                          Gemini 자료 검토 결과 (취/버림 + 결함 + 갭)
├── Doxyfile                           소스 브라우저 + @req/@verifies 렌더링 설정
├── .github/workflows/
│   ├── cicd-ct.yml                    CI/CD/CT 파이프라인 (트리거 4종)
│   └── pages.yml                      코드 인덱스 사이트 빌드 및 Pages 배포
├── docs/
│   ├── DEMO_SCENARIO.md               세미나 진행 시나리오 (발표 멘트 포함)
│   ├── TRACEABILITY_LINKING.md        안 끊어지는 코드 링크 체계 설명
│   ├── SRS_AEB_Requirements.md        SWE.1 요구사항 명세 (승인 15건 + 제안 3건)
│   ├── SRS_AEB_Requirements.csv       └ Codebeamer 임포트용 (UTF-8 BOM)
│   ├── SDD_AEB_Design.md              SWE.3 상세 설계 + 코드 링크 (8절)
│   ├── Traceability_Matrix.csv        요구사항 ↔ 심볼 ↔ 테스트 (심볼 기반)
│   ├── generated/
│   │   └── CODE_INDEX.md              자동 생성 인덱스 스냅샷 + 추적성 갭
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
│   └── Aeb_FusionEngine.c             TTC 계산 및 제동 판단 (@req 주석 포함)
├── test/
│   ├── test_Aeb_FusionEngine.cpp      단위시험 (GTest/GMock, 4 케이스, @verifies)
│   ├── Aeb_TestHarness.c              SIL 하네스 (Mock 센서 + ctypes 노출 래퍼)
│   └── test_functional_scenario.py    기능시험 시계열 시나리오 (6 케이스, @verifies)
└── scripts/
    ├── build_symbol_map.py            심볼/요구사항 인덱스 생성
    ├── generate_redirects.py          sym/ req/ 리다이렉트 페이지 생성
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

코드 인덱스 생성 (Doxygen 없이도 동작, ctags 없으면 정규식 폴백):

```bash
python3 scripts/build_symbol_map.py
python3 scripts/generate_redirects.py
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

1. **GitHub Pages 활성화** — Settings → Pages → Source 를 **GitHub Actions** 로 설정.
   설정 전까지는 `sym/` `req/` 안정 링크가 404 다. 데모의 추적성 링크 전부가 여기에 걸려 있다.
2. **Codebeamer `automatedtestruns` 스키마 대조** — 대상 서버가 전 요청에 HTTP 500 응답 중이라 실측 검증 보류. 서버 복구 후 `--dry-run` 출력과 swagger 스키마 대조 필요.
3. **Codebeamer 트래커 구성** — Requirements / Test Case / Test Run / Bug 4종 생성 및 SRS CSV 임포트, ASIL·Verification Method 커스텀 필드 추가. 요구사항 항목에 `req/<ID>/` 링크를 담을 URL 필드 추가.
4. **Codebeamer 워크플로우 액션 배선** — `cb_trigger_ci.py` 를 전환 액션에 연결 (스크립트 실행 권한 확인 필요).
5. **Codebeamer MCP 대화형 시연 스크립트** — 질의 3~4개 확정 및 리허설.
6. GTest/GMock 환경에서 단위 시험 실패 2건 재현 확인 (현재는 컴파일러 경고로만 확인).
7. 임시 파일 2개 삭제 (위 "정리 대상 임시 파일" 참조).
