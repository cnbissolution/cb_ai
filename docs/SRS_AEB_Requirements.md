# [SWE.1] AEB 소프트웨어 요구사항 명세서 (SRS)

- 대상 컴포넌트: `Aeb_FusionEngine` (AEB 센서 퓨전 / 제동 판단 엔진)
- 근거 표준: ASPICE SWE.1 / ISO 26262
- 임포트 대상: Codebeamer `Software Requirements` 트래커 (CSV: `SRS_AEB_Requirements.csv`)
- 출처: Gemini 세션 산출물 2개 버전(15항목 상세판 + 8항목 ASIL판)을 **병합**한 것

## 1. 요구사항 목록

| Req ID | Parent | Type | ASIL | Requirement Text (Shall Statement) | Verification (SWE.4) |
|---|---|---|---|---|---|
| SYS-AEB-100 | - | Heading | - | AEB 시스템 초기화 및 인터페이스 | - |
| SRS-AEB-101 | SYS-AEB-100 | Functional | QM | 시스템은 레이더, 카메라, 제동 액추에이터 인터페이스 포인터를 검증하고 컨텍스트에 할당하여 초기화해야 한다. | Unit Test |
| SRS-AEB-102 | SYS-AEB-100 | Functional | QM | 시스템 초기화 시 내부 결함(Fault) 상태를 FALSE로 설정해야 한다. | Unit Test |
| SRS-AEB-103 | SYS-AEB-100 | Functional | QM | 시스템 초기화 시 충돌 예상 시간(TTC)을 안전 기본값 999.0초로 설정해야 한다. | Unit Test |
| SYS-AEB-200 | - | Heading | - | 태스크 스케줄링 및 결함 모니터링 (Fail-Safe) | - |
| SRS-AEB-201 | SYS-AEB-200 | Constraint | ASIL-D | AEB 메인 제어 로직은 10ms 주기로 실행되어야 한다. | Integration / Timing |
| SRS-AEB-202 | SYS-AEB-200 | Safety | ASIL-D | 시스템은 매 제어 주기마다 레이더 센서의 상태(Sensor Status)를 확인해야 한다. | Unit Test |
| SRS-AEB-203 | SRS-AEB-202 | Safety | ASIL-D | 레이더 센서 상태가 정상(0x00)이 아닐 경우, 시스템은 내부 결함 플래그를 TRUE로 설정해야 한다. | Fault Injection |
| SRS-AEB-204 | SRS-AEB-203 | Safety | ASIL-D | 결함이 감지된 경우, 시스템은 즉시 브레이크를 해제(Release)하고 해당 주기의 제어 로직을 종료해야 한다. | Fault Injection |
| SYS-AEB-300 | - | Heading | - | 센서 데이터 퓨전 및 충돌 판단 (TTC) | - |
| SRS-AEB-301 | SYS-AEB-300 | Functional | ASIL-B | 시스템은 레이더와 카메라로부터 타겟 객체(Target Object) 데이터를 수집해야 한다. | Unit Test |
| SRS-AEB-302 | SYS-AEB-300 | Functional | ASIL-D | 수집된 레이더 타겟이 유효(Valid)하고 상대 속도가 -0.5 km/h 미만(가까워지는 상태)일 경우에만 TTC를 계산해야 한다. | Boundary Value |
| SRS-AEB-303 | SRS-AEB-302 | Functional | ASIL-D | TTC는 레이더 타겟의 거리(m)를 상대 속도(m/s)로 나누어 계산해야 한다. | Unit Test |
| SRS-AEB-304 | SRS-AEB-302 | Functional | ASIL-D | 레이더 타겟이 유효하지 않거나 멀어지는 상태일 경우, TTC는 999.0초로 유지되어야 한다. | Equivalence |
| SRS-AEB-305 | SYS-AEB-300 | Functional | ASIL-A | 카메라 센서를 통해 보행자가 감지된 경우, 계산된 TTC 값에 0.8의 가중치를 곱하여 반영해야 한다. | Equivalence |
| SYS-AEB-400 | - | Heading | - | 제동 액추에이터 제어 (Actuation) | - |
| SRS-AEB-401 | SYS-AEB-400 | Safety | ASIL-D | 최종 계산된 TTC가 임계값 1.5초 미만일 경우, 제동 액추에이터에 100%의 긴급 제동 명령을 인가해야 한다. | Boundary Value |
| SRS-AEB-402 | SYS-AEB-400 | Safety | ASIL-D | 최종 계산된 TTC가 1.5초 이상이거나 유효한 타겟이 없을 경우, 제동 액추에이터에 브레이크 해제 명령을 인가해야 한다. | Unit Test |

## 2. 제안(후보) 요구사항 — 코드에는 있으나 요구사항이 없는 항목

> 데모 스토리 포인트: **"AI가 코드에서 요구사항 누락(orphan implementation)을 찾아난다"**
> 아래 3건은 Gemini 원본 SRS에 없으나 코드/테스트에는 구현되어 있어, 승인 전 후보 상태로 분리해 둔다.

| 후보 ID | Type | ASIL | Requirement Text | 근거 |
|---|---|---|---|---|
| SRS-AEB-205 (제안) | Safety | ASIL-D | 메인 함수 진입 시 컨텍스트 및 하위 인터페이스 포인터의 NULL 여부를 검증하고, 미할당 시 제어 로직을 수행하지 않아야 한다. | 코드 `Aeb_FusionEngine.c:54-57`, 테스트 `NullPointer_Injection_NoCrash` |
| SRS-AEB-206 (제안) | Safety | ASIL-D | 인터페이스 함수 포인터 호출 직전에 해당 포인터의 유효성을 검증해야 한다. | 코드 전반 `!= NULL_PTR` 가드 |
| SRS-AEB-306 (보류) | Functional | ASIL-D | 상대 속도(m/s)가 0.01 m/s 이하일 경우 나눗셈을 수행하지 않고 안전 기본값을 유지해야 한다. | 코드 `Aeb_FusionEngine.c:34` — **단, SRS-AEB-302의 -0.5 km/h 가드로 인해 도달 불가(dead code). REVIEW.md D-2 참조** |

## 3. Codebeamer 임포트 시 권장 속성 매핑

| Codebeamer 필드 | 값 / 소스 |
|---|---|
| Name | Requirement Text 앞 40자 요약 |
| Description | Requirement Text 전문 |
| Type / Category | Functional / Safety / Constraint / Heading |
| ASIL (Custom choice) | QM / ASIL-A / ASIL-B / ASIL-D |
| Verification Method (Custom choice) | Unit Test / Boundary Value / Equivalence / Fault Injection / Integration |
| Parent | 계직 구조(SYS-AEB-x00 → SRS-AEB-xxx) |
| Downstream Ref | Traceability_Matrix.csv 의 Test Case 컬럼 → Test Case 트래커 링크 |
