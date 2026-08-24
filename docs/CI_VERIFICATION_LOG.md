# CI 실행으로 확인된 사실 (2026-08-24)

로컬 환경(Windows, GTest/Doxygen/ctags 없음)에서 검증할 수 없어 "미검증"으로
남겨두었던 항목들이 CI 와 실서버에서 어떻게 판명됐는지 기록한다.

## 1. 확인된 것

| 항목 | 이전 상태 | 결과 |
|---|---|---|
| Doxygen 사이트 빌드 | 미검증 (로컬에 doxygen 없음) | ✅ CI build 잡 전 단계 성공 |
| ctags 심볼 인덱싱 | 미검증 (로컬에 ctags 없음) | ✅ 성공 — 단, 버그 1건 발견 (아래 2절) |
| `sym/` `req/` 리다이렉트 | 미검증 | ✅ 배포 후 200, 링크 대상 라인 범위 정확 |
| **단위시험 2건 실패 (D-1)** | **컴파일러 경고로만 추정** | ✅ **실제 GTest 환경에서 재현** |
| 커버리지 게이트 미달 (D-2/G-2) | 미검증 | ✅ gcovr exit 4 (브랜치 임계 미달) |
| 기능시험 SIL 6건 | 로컬 통과 | ✅ CI 에서도 통과 (실패 목록에 없음) |
| 실패해도 증적 아카이브 (D-3 항목5) | 설계만 | ✅ 시험 실패 상태에서 아티팩트 업로드 성공 |
| Codebeamer 필드 매핑 (D-5) | "[검증 필요]" | ✅ 실측 스키마 대조 완료 — 오류 2건 발견 |

### 근거

CI 체크런 annotation (run 32654599107):

```
[failure] 단위 시험 실패          <- D-1, 최종 판정 게이트가 남긴 ::error::
[failure] 커버리지 임계 미달       <- D-2 / G-2
[failure] Process completed with exit code 4   <- gcovr 브랜치 임계 미달
[failure] Process completed with exit code 2   <- upload_to_codebeamer (secrets 미설정)
```

`기능 시험 실패` 는 목록에 없다. SIL 6건은 CI 에서도 전부 통과했다.

`단위 시험` 스텝의 conclusion 은 `success` 로 보이는데 이는 `continue-on-error: true`
때문이며, 실제 결과(outcome)는 최종 판정 게이트가 annotation 으로 남긴다.
스텝 표시만 보고 통과했다고 판단하면 안 된다.

## 2. CI 에서만 드러난 버그 — ctags 가 TEST_F 를 함수로 오인

로컬에는 ctags 가 없어 정규식 폴백만 돌았기 때문에 재현되지 않았다.

- ctags 가 `TEST_F(Suite, Name) {` 를 `TEST_F` 라는 함수 정의로 인식
- 요구사항 페이지마다 심볼명이 `TEST_F` 인 가짜 행이 1개씩 섞임
  (SRS-AEB-305 는 6행 중 2행이 가짜)
- 심볼 맵에서는 4개 케이스가 같은 키로 충돌해 마지막 것만 남음

수정: `MACRO_NAMES` 집합으로 ctags/정규식 양쪽 결과에서 제외.
실제 테스트 이름은 기존대로 `TEST_F_RE` 정규식이 공급한다.

> **교훈**: 폴백 경로만 로컬에서 돌려보고 "검증했다"고 하면 안 된다.
> 주 경로(ctags)와 폴백 경로(정규식)는 서로 다른 결과를 낼 수 있다.

## 3. 브랜치 커버리지 63.89% 의 정체

`coverage_branch_analysis.txt` 참조. 미실행 분기 13개가 전부 이미 식별된
3개 요구사항으로 설명된다 — 테스트를 빠뜨려서가 아니다.

| 요구사항 | 분기 수 | 성격 |
|---|---|---|
| SRS-AEB-205 (제안, 미승인) | 4 | 요구사항 승인되면 테스트 붙일 수 있음 |
| SRS-AEB-206 (제안, 미승인) | 8 | 위와 동일 |
| SRS-AEB-306 (보류, 도달불가) | 1 | **테스트로 해결 불가. 코드를 고쳐야 함** |

gcov 가 `L49 branch 1 taken 0` 으로 보고했다. `d2_dead_branch_probe.py` 의
스윕 분석과 **독립적으로 같은 결론**에 도달한 것이다.

## 4. Codebeamer 스키마 실측 결과

대상: Automotive Template 3.0 (project 44) → Test Runs 트래커 123469

| 발견 | 내용 |
|---|---|
| 오류 1 | `Passed`/`Failed` 를 `status` 에 보내고 있었다. Status 옵션에는 그런 값이 없다 (Unset/In progress/Suspended/Finished/Closed/…). `result` 필드로 보내야 한다 |
| 오류 2 | `testCases` (TableField) 가 전 상태에서 필수다. Test Case 참조 없이는 생성 거부. `CB_TEST_CASE_TRACKER_ID` 는 선택이 아니라 필수 |
| 누락 | `build` 전용 TextField 가 있는데 description 문자열에만 넣고 있었다 |

대응으로 `--check-schema` 프리플라이트를 추가했다. 전송 전에 실제 옵션 이름과
대조하므로, 다국어 인스턴스(옵션명이 로컬라이즈됨)에서도 안전하다.

## 5. 아직 검증하지 못한 것

| 항목 | 사유 |
|---|---|
| `automatedtestruns` 요청 **본문 스키마** | 서버에 OpenAPI 스펙 엔드포인트가 노출되지 않음. 필드명은 트래커 스키마로 확정했으나 요청 봉투(envelope) 형태는 문서 기준 추정 |
| 실제 Test Run 생성 | Secrets 미설정 + 실 데이터 생성은 승인 필요 |
| AI 실패 분석 실행 | `ANTHROPIC_API_KEY` 미설정 |
| Codebeamer → CI `repository_dispatch` | Codebeamer 워크플로우 액션 배선 필요 |

데모 전 `--check-schema` 와 `--dry-run` 을 대상 인스턴스에서 한 번씩 돌려
위 추정 부분을 확정할 것.
