# [SWE.3] AEB 센서 퓨전 엔진 소프트웨어 상세 설계서 (SDD)

- 대상 컴포넌트: `Aeb_FusionEngine`
- 근거 표준: ASPICE SWE.2 / SWE.3, ISO 26262
- 임포트 대상: Codebeamer Wiki 또는 `Software Architecture / Design` 트래커

## 1. 아키텍처 개요 (Architecture Overview)

AEB(Autonomous Emergency Braking) 시스템은 하드웨어 종속성을 제거하기 위해
**의존성 역전 원칙(DIP)** 을 적용하여 설계되었다. 메인 제어 로직(`Aeb_FusionEngine`)은
구체적인 하드웨어 드라이버 대신 추상화된 함수 포인터 인터페이스
(`IRadarSensor`, `ICameraSensor`, `IBrakeActuator`)에만 의존한다.
이를 통해 센서/액추에이터 하드웨어가 변경되어도 제어 알고리즘 코드는 수정 없이 재사용 가능하며,
단위 시험 시 Mock 객체 주입이 가능하다 (→ SWE.4 검증 전략의 전제 조건).

- 정적 구조: `diagrams/aeb_class.puml`
- 동적 행위: `diagrams/aeb_sequence_10ms.puml`
- 소스 브라우저: https://cnbissolution.github.io/cb_ai/ (Doxygen, 호출 그래프 포함)

| 설계 요소 | 구현 심볼 | 코드 링크 (안정) |
|---|---|---|
| 초기화 / 의존성 주입 | `Aeb_Init` | [sym/src/Aeb_FusionEngine.c/Aeb_Init](https://cnbissolution.github.io/cb_ai/sym/src/Aeb_FusionEngine.c/Aeb_Init/) |
| TTC 산출 (내부) | `CalculateTTC` | [sym/src/Aeb_FusionEngine.c/CalculateTTC](https://cnbissolution.github.io/cb_ai/sym/src/Aeb_FusionEngine.c/CalculateTTC/) |
| 10ms 제어 루프 | `Aeb_MainFunction_10ms` | [sym/src/Aeb_FusionEngine.c/Aeb_MainFunction_10ms](https://cnbissolution.github.io/cb_ai/sym/src/Aeb_FusionEngine.c/Aeb_MainFunction_10ms/) |
| SIL 테스트 하네스 | `Aeb_Init_Wrapper` 외 | [sym/test/Aeb_TestHarness.c/Aeb_Init_Wrapper](https://cnbissolution.github.io/cb_ai/sym/test/Aeb_TestHarness.c/Aeb_Init_Wrapper/) |

> 위 링크는 **심볼 이름 기준**이라 라인 번호가 바뀌어도 유효하다.
> 링크 체계는 [TRACEABILITY_LINKING.md](TRACEABILITY_LINKING.md) 참조.

## 2. 데이터 구조 설계 (Data Dictionary)

| 데이터 타입 | 멤버 변수 (타입) | 유효 범위 | 설명 |
|---|---|---|---|
| `TargetObject` | `Distance_M` (float32) | 0.0 ~ 150.0 m | 전방 타겟과의 절대 거리 |
| | `RelativeSpeed_Kmph` (float32) | -200.0 ~ 200.0 km/h | 타겟과의 상대 속도 (**음수 = 가까워짐**) |
| | `IsValid` (boolean) | TRUE / FALSE | 타겟 데이터 유효성 플래그 |
| `Aeb_SystemContext` | `Radar` / `Camera` / `Brake` (ptr) | non-NULL | 주입된 인터페이스 포인터 |
| | `IsSystemFault` (boolean) | TRUE / FALSE | TRUE 시 제어 중단 및 페일세이프 진입 |
| | `CalculatedTTC` (float32) | 0.0 ~ 999.0 s | 퓨전 로직이 산출한 최종 TTC |

## 3. 상수 및 캘리브레이션 파라미터 (Magic Number 제거)

| 매크로 | 값 | 설명 |
|---|---|---|
| `AEB_TTC_CRITICAL_SEC` | 1.5F | 제동 트리거 임계 시간 (초) |
| `AEB_TTC_SAFE_DEFAULT` | 999.0F | 위험 타겟 없음을 의미하는 기본 안전값 |
| `AEB_PEDESTRIAN_WEIGHT` | 0.8F | 보행자 감지 시 TTC 위험 가중치 |
| `AEB_MAX_BRAKE_FORCE_PCT` | 100.0F | 긴급 제동 시 최대 제동력 (%) |
| `AEB_REL_SPEED_EPSILON_MPS` | 0.01F | 0으로 나누기 방지용 최소 분모 (m/s) |
| `AEB_KMPH_TO_MPS(kmph)` | `(kmph)/3.6F` | 단위 환산 매크로 |

## 4. 외부 인터페이스 설계 (Interface Design)

### 4.1 센서 입력 (Sensor Inputs)
- `IRadarSensor::GetSensorStatus() -> uint8`
  - 레이더 자기진단 상태. **0x00 = 정상**, 그 외 = 결함.
- `IRadarSensor::GetRadarTarget(TargetObject* out_target)`
  - 신호 처리부가 선별한 최우선 위협 타겟 1개를 call-by-reference로 반환.
- `ICameraSensor::IsPedestrianDetected() -> boolean`
  - 비전 알고리즘 기반 주행 경로 내 보행자 존재 여부.
- `ICameraSensor::GetCameraTarget(TargetObject* out_target)`
  - **인터페이스로 정의되어 있으나 현재 퓨전 로직에서 호출되지 않음 (REVIEW.md D-1)**

### 4.2 액추에이터 출력 (Actuator Outputs)
- `IBrakeActuator::ApplyEmergencyBrake(float32 brakeForce_Pct)` — ESP/ESC에 유압 생성 요청 (0.0~100.0%)
- `IBrakeActuator::ReleaseBrake()` — 제동 해제 / 안전 상태 복귀

## 5. 핵심 알고리즘: TTC 계산

```
relSpeed_Mps = (-RelativeSpeed_Kmph) / 3.6
TTC          = Distance_M / relSpeed_Mps      (단, relSpeed_Mps > 0.01 일 때)
TTC_final    = TTC * 0.8                      (보행자 감지 시)
```

판단:
- `TTC_final < 1.5` → `ApplyEmergencyBrake(100.0)`
- 그 외 → `ReleaseBrake()`

### 경계값 설계 근거 (단위 시험 설계와 직결)
- 거리 18m / 상대속도 -36km/h(-10m/s) → 기본 TTC = **1.8s** → 미제동
- 동일 조건 + 보행자 감지 → 1.8 × 0.8 = **1.44s** → **제동 발동**
- 이 한 쌍이 SRS-AEB-305 와 SRS-AEB-401 의 **상호작용**을 증명하는 핵심 경계값 페어이다.

## 6. 예외 처리 및 페일세이프 (Fail-Safe) 설계

| 예외 상황 | 검출 방법 | 조치 |
|---|---|---|
| 센서 결함 | `GetSensorStatus() != 0x00U` | `IsSystemFault = TRUE`, `ReleaseBrake()`, 즉시 return |
| 컨텍스트/인터페이스 미할당 | `context`, `Radar`, `Camera`, `Brake` NULL 체크 | 제어 로직 수행 없이 즉시 return |
| 함수 포인터 미할당 | 호출 직전 `!= NULL_PTR` | 해당 호출 스킵 (기본값 유지) |
| 타겟 무효 / 이탈 | `IsValid == FALSE` 또는 `RelSpeed >= -0.5 km/h` | TTC 연산 우회, 999.0초 유지 |
| 0으로 나누기 | `relSpeed_Mps > 0.01F` | 나눗셈 스킵 (**현재 도달 불가 — REVIEW.md D-2**) |

## 7. MISRA-C:2012 준수 현황

| 지침 | 적용 내용 |
|---|---|
| Dir 4.1 (런타임 실패) | 포인터/함수 포인터 NULL 검증, 나눗셈 분모 검증 |
| Rule 2.5 / 10.4 | 매직 넘버 전량 매크로화 (999.0, 0.8, 100.0, 1.5) |
| Rule 14.3 | 불변 조건 제거 필요 — **AEB_REL_SPEED_EPSILON 검사가 항상 참 (위배 소지)** |
| Rule 15.5 | 단일 return 원칙 — `Aeb_MainFunction_10ms` 에 다중 return 존재 (편차 승인 필요) |

## 8. 요구사항 ↔ 설계 ↔ 코드 추적 링크

소스의 `@req` / `@verifies` 주석을 CI 가 파싱해 자동 생성한다.
라인 번호는 매 빌드마다 재계산되므로 아래 링크는 코드가 이동해도 깨지지 않는다.

| 요구사항 | 구현 심볼 | 검증 |
|---|---|---|
| [`SRS-AEB-101`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-101/) | `Aeb_Init` | 0건 |
| [`SRS-AEB-102`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-102/) | `Aeb_Init` | 2건 |
| [`SRS-AEB-103`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-103/) | `Aeb_Init` | 2건 |
| [`SRS-AEB-201`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-201/) | `Aeb_MainFunction_10ms` | 0건 |
| [`SRS-AEB-202`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-202/) | `Aeb_MainFunction_10ms` | 1건 |
| [`SRS-AEB-203`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-203/) | `Aeb_MainFunction_10ms` | 1건 |
| [`SRS-AEB-204`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-204/) | `Aeb_MainFunction_10ms` | 1건 |
| [`SRS-AEB-205`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-205/) | — | 1건 |
| [`SRS-AEB-206`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-206/) | — | 1건 |
| [`SRS-AEB-301`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-301/) | `Aeb_MainFunction_10ms` | 1건 |
| [`SRS-AEB-302`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-302/) | `CalculateTTC` | 3건 |
| [`SRS-AEB-303`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-303/) | `CalculateTTC` | 1건 |
| [`SRS-AEB-304`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-304/) | `CalculateTTC` | 3건 |
| [`SRS-AEB-305`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-305/) | `Aeb_MainFunction_10ms` | 3건 |
| [`SRS-AEB-306`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-306/) | `CalculateTTC` | 0건 |
| [`SRS-AEB-401`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-401/) | `Aeb_MainFunction_10ms` | 2건 |
| [`SRS-AEB-402`](https://cnbissolution.github.io/cb_ai/req/SRS-AEB-402/) | `Aeb_MainFunction_10ms` | 2건 |

- 전체 인덱스: [generated/CODE_INDEX.md](generated/CODE_INDEX.md) (자동 생성)
- 매트릭스: [Traceability_Matrix.csv](Traceability_Matrix.csv)
- 링크 체계 설명: [TRACEABILITY_LINKING.md](TRACEABILITY_LINKING.md)

### 자동 도출된 추적성 갭

| 요구사항 | 갭 |
|---|---|
| `SRS-AEB-101` | 검증 없음 — 초기화 전용 테스트 미작성 |
| `SRS-AEB-201` | 검증 없음 — 10ms 주기는 코드로 검증 불가 (설계 리뷰 대상) |
| `SRS-AEB-205`, `SRS-AEB-206` | 고아 테스트 — 테스트는 있으나 요구사항이 미승인 상태 |
| `SRS-AEB-306` | 검증 없음 — 도달 불가 코드라 검증 자체가 불가 (REVIEW.md D-2) |
