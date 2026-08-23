# 소스 코드 인덱스 (자동 생성)

> `scripts/build_symbol_map.py` 가 생성한다. 직접 수정하지 물 것.
> 라인 번호는 생성 시점 기준이며, 링크는 심볼 이름 기준이라 라인이 바뀜도 유효하다.
> 장재소에 커밋된 파일은 스냅샷이다. 최신본은 CI 아티팩트(`code-index`)와 GitHub Pages 를 보라.

- 대상: `cnbissolution/cb_ai` @ `main`
- **Base URL**: https://cnbissolution.github.io/cb_ai — 아래 링크는 이 주소 기준 상대 경로다.
- 안정 링크 형식: `https://cnbissolution.github.io/cb_ai/sym/<경로>/<심볼>/`
- 요구사항 링크 형식: `https://cnbissolution.github.io/cb_ai/req/<요구사항ID>/`

## 1. 요구사항 → 코드 (ALM 에 걸 링크)

| 요구사항 | 관계 | 심볼 | 위치 | 안정 링크 |
|---|---|---|---|---|
| `SRS-AEB-101` | 구현 | `Aeb_Init` | src/Aeb_FusionEngine.c:18-27 | `req/SRS-AEB-101/` |
| `SRS-AEB-102` | 구현 | `Aeb_Init` | src/Aeb_FusionEngine.c:18-27 | `req/SRS-AEB-102/` |
| `SRS-AEB-102` | 검증 | `test_initial_state_is_safe` | test/test_functional_scenario.py:81-89 | `req/SRS-AEB-102/` |
| `SRS-AEB-102` | 검증 | `test_functional_scenario_emergency_braking` | test/test_functional_scenario.py:92-120 | `req/SRS-AEB-102/` |
| `SRS-AEB-103` | 구현 | `Aeb_Init` | src/Aeb_FusionEngine.c:18-27 | `req/SRS-AEB-103/` |
| `SRS-AEB-103` | 검증 | `test_initial_state_is_safe` | test/test_functional_scenario.py:81-89 | `req/SRS-AEB-103/` |
| `SRS-AEB-103` | 검증 | `test_functional_scenario_emergency_braking` | test/test_functional_scenario.py:92-120 | `req/SRS-AEB-103/` |
| `SRS-AEB-201` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-201/` |
| `SRS-AEB-202` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-202/` |
| `SRS-AEB-202` | 검증 | `test_functional_scenario_sensor_fault_failsafe` | test/test_functional_scenario.py:146-167 | `req/SRS-AEB-202/` |
| `SRS-AEB-203` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-203/` |
| `SRS-AEB-203` | 검증 | `test_functional_scenario_sensor_fault_failsafe` | test/test_functional_scenario.py:146-167 | `req/SRS-AEB-203/` |
| `SRS-AEB-204` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-204/` |
| `SRS-AEB-204` | 검증 | `test_functional_scenario_sensor_fault_failsafe` | test/test_functional_scenario.py:146-167 | `req/SRS-AEB-204/` |
| `SRS-AEB-205` | 검증 | `NullPointer_Injection_NoCrash` | test/test_Aeb_FusionEngine.cpp:163-171 | `req/SRS-AEB-205/` |
| `SRS-AEB-206` | 검증 | `NullPointer_Injection_NoCrash` | test/test_Aeb_FusionEngine.cpp:163-171 | `req/SRS-AEB-206/` |
| `SRS-AEB-301` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-301/` |
| `SRS-AEB-301` | 검증 | `PedestrianWeight_TriggersEmergencyBrake` | test/test_Aeb_FusionEngine.cpp:87-103 | `req/SRS-AEB-301/` |
| `SRS-AEB-302` | 구현 | `CalculateTTC` | src/Aeb_FusionEngine.c:36-55 | `req/SRS-AEB-302/` |
| `SRS-AEB-302` | 검증 | `CalculateTTC_DivideByZero_Prevention` | test/test_Aeb_FusionEngine.cpp:139-153 | `req/SRS-AEB-302/` |
| `SRS-AEB-302` | 검증 | `test_functional_scenario_target_receding_no_braking` | test/test_functional_scenario.py:170-179 | `req/SRS-AEB-302/` |
| `SRS-AEB-302` | 검증 | `test_functional_scenario_invalid_target_no_braking` | test/test_functional_scenario.py:182-190 | `req/SRS-AEB-302/` |
| `SRS-AEB-303` | 구현 | `CalculateTTC` | src/Aeb_FusionEngine.c:36-55 | `req/SRS-AEB-303/` |
| `SRS-AEB-303` | 검증 | `test_functional_scenario_emergency_braking` | test/test_functional_scenario.py:92-120 | `req/SRS-AEB-303/` |
| `SRS-AEB-304` | 구현 | `CalculateTTC` | src/Aeb_FusionEngine.c:36-55 | `req/SRS-AEB-304/` |
| `SRS-AEB-304` | 검증 | `CalculateTTC_DivideByZero_Prevention` | test/test_Aeb_FusionEngine.cpp:139-153 | `req/SRS-AEB-304/` |
| `SRS-AEB-304` | 검증 | `test_functional_scenario_target_receding_no_braking` | test/test_functional_scenario.py:170-179 | `req/SRS-AEB-304/` |
| `SRS-AEB-304` | 검증 | `test_functional_scenario_invalid_target_no_braking` | test/test_functional_scenario.py:182-190 | `req/SRS-AEB-304/` |
| `SRS-AEB-305` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-305/` |
| `SRS-AEB-305` | 검증 | `PedestrianWeight_TriggersEmergencyBrake` | test/test_Aeb_FusionEngine.cpp:87-103 | `req/SRS-AEB-305/` |
| `SRS-AEB-305` | 검증 | `NoPedestrian_TtcAboveThreshold_ReleasesBrake` | test/test_Aeb_FusionEngine.cpp:113-127 | `req/SRS-AEB-305/` |
| `SRS-AEB-305` | 검증 | `test_functional_scenario_pedestrian_weight_advances_braking` | test/test_functional_scenario.py:123-143 | `req/SRS-AEB-305/` |
| `SRS-AEB-306` | 구현 | `CalculateTTC` | src/Aeb_FusionEngine.c:36-55 | `req/SRS-AEB-306/` |
| `SRS-AEB-401` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-401/` |
| `SRS-AEB-401` | 검증 | `PedestrianWeight_TriggersEmergencyBrake` | test/test_Aeb_FusionEngine.cpp:87-103 | `req/SRS-AEB-401/` |
| `SRS-AEB-401` | 검증 | `test_functional_scenario_emergency_braking` | test/test_functional_scenario.py:92-120 | `req/SRS-AEB-401/` |
| `SRS-AEB-402` | 구현 | `Aeb_MainFunction_10ms` | src/Aeb_FusionEngine.c:70-122 | `req/SRS-AEB-402/` |
| `SRS-AEB-402` | 검증 | `NoPedestrian_TtcAboveThreshold_ReleasesBrake` | test/test_Aeb_FusionEngine.cpp:113-127 | `req/SRS-AEB-402/` |
| `SRS-AEB-402` | 검증 | `test_functional_scenario_emergency_braking` | test/test_functional_scenario.py:92-120 | `req/SRS-AEB-402/` |

## 2. 추적성 갭 (자동 도출)

| 요구사항 | 갭 | 설명 |
|---|---|---|
| `SRS-AEB-101` | **검증 없음** | 구현은 있으나 이를 검증하는 테스트가 없다 |
| `SRS-AEB-201` | **검증 없음** | 구현은 있으나 이를 검증하는 테스트가 없다 |
| `SRS-AEB-205` | **고아 테스트** | 테스트는 있으나 구현에 @req 표기가 없다 (요구사항 미승인 가능) |
| `SRS-AEB-206` | **고아 테스트** | 테스트는 있으나 구현에 @req 표기가 없다 (요구사항 미승인 가능) |
| `SRS-AEB-306` | **검증 없음** | 구현은 있으나 이를 검증하는 테스트가 없다 |

## 3. 전체 심볼

| 파일 | 심볼 | 라인 | 요구사항 | 안정 링크 |
|---|---|---|---|---|
| `src/Aeb_FusionEngine.c` | `Aeb_Init` | 18-27 | `SRS-AEB-101`, `SRS-AEB-102`, `SRS-AEB-103` | `sym/src/Aeb_FusionEngine.c/Aeb_Init/` |
| `src/Aeb_FusionEngine.c` | `CalculateTTC` | 36-55 | `SRS-AEB-302`, `SRS-AEB-303`, `SRS-AEB-304`, `SRS-AEB-306` | `sym/src/Aeb_FusionEngine.c/CalculateTTC/` |
| `src/Aeb_FusionEngine.c` | `Aeb_MainFunction_10ms` | 70-122 | `SRS-AEB-201`, `SRS-AEB-202`, `SRS-AEB-203`, `SRS-AEB-204`, `SRS-AEB-301`, `SRS-AEB-305`, `SRS-AEB-401`, `SRS-AEB-402` | `sym/src/Aeb_FusionEngine.c/Aeb_MainFunction_10ms/` |
| `test/Aeb_TestHarness.c` | `Mock_GetRadarTarget` | 34-37 | - | `sym/test/Aeb_TestHarness.c/Mock_GetRadarTarget/` |
| `test/Aeb_TestHarness.c` | `Mock_GetSensorStatus` | 39-42 | - | `sym/test/Aeb_TestHarness.c/Mock_GetSensorStatus/` |
| `test/Aeb_TestHarness.c` | `Mock_GetCameraTarget` | 44-47 | - | `sym/test/Aeb_TestHarness.c/Mock_GetCameraTarget/` |
| `test/Aeb_TestHarness.c` | `Mock_IsPedestrianDetected` | 49-52 | - | `sym/test/Aeb_TestHarness.c/Mock_IsPedestrianDetected/` |
| `test/Aeb_TestHarness.c` | `Mock_ApplyEmergencyBrake` | 54-58 | - | `sym/test/Aeb_TestHarness.c/Mock_ApplyEmergencyBrake/` |
| `test/Aeb_TestHarness.c` | `Mock_ReleaseBrake` | 60-64 | - | `sym/test/Aeb_TestHarness.c/Mock_ReleaseBrake/` |
| `test/Aeb_TestHarness.c` | `Aeb_Init_Wrapper` | 75-90 | - | `sym/test/Aeb_TestHarness.c/Aeb_Init_Wrapper/` |
| `test/Aeb_TestHarness.c` | `Aeb_MainFunction_10ms_Wrapper` | 92-95 | - | `sym/test/Aeb_TestHarness.c/Aeb_MainFunction_10ms_Wrapper/` |
| `test/Aeb_TestHarness.c` | `SetMockRadarTarget` | 98-103 | - | `sym/test/Aeb_TestHarness.c/SetMockRadarTarget/` |
| `test/Aeb_TestHarness.c` | `SetMockPedestrianDetected` | 105-108 | - | `sym/test/Aeb_TestHarness.c/SetMockPedestrianDetected/` |
| `test/Aeb_TestHarness.c` | `SetMockSensorStatus` | 110-113 | - | `sym/test/Aeb_TestHarness.c/SetMockSensorStatus/` |
| `test/Aeb_TestHarness.c` | `GetBrakeCommand` | 116-119 | - | `sym/test/Aeb_TestHarness.c/GetBrakeCommand/` |
| `test/Aeb_TestHarness.c` | `GetCalculatedTTC` | 121-124 | - | `sym/test/Aeb_TestHarness.c/GetCalculatedTTC/` |
| `test/Aeb_TestHarness.c` | `GetSystemFaultFlag` | 126-129 | - | `sym/test/Aeb_TestHarness.c/GetSystemFaultFlag/` |
| `test/Aeb_TestHarness.c` | `GetApplyBrakeCallCount` | 131-134 | - | `sym/test/Aeb_TestHarness.c/GetApplyBrakeCallCount/` |
| `test/Aeb_TestHarness.c` | `GetReleaseBrakeCallCount` | 136-139 | - | `sym/test/Aeb_TestHarness.c/GetReleaseBrakeCallCount/` |
| `test/test_Aeb_FusionEngine.cpp` | `PedestrianWeight_TriggersEmergencyBrake` | 87-103 | `SRS-AEB-305`, `SRS-AEB-401`, `SRS-AEB-301` | `sym/test/test_Aeb_FusionEngine.cpp/PedestrianWeight_TriggersEmergencyBrake/` |
| `test/test_Aeb_FusionEngine.cpp` | `NoPedestrian_TtcAboveThreshold_ReleasesBrake` | 113-127 | `SRS-AEB-402`, `SRS-AEB-305` | `sym/test/test_Aeb_FusionEngine.cpp/NoPedestrian_TtcAboveThreshold_ReleasesBrake/` |
| `test/test_Aeb_FusionEngine.cpp` | `CalculateTTC_DivideByZero_Prevention` | 139-153 | `SRS-AEB-302`, `SRS-AEB-304` | `sym/test/test_Aeb_FusionEngine.cpp/CalculateTTC_DivideByZero_Prevention/` |
| `test/test_Aeb_FusionEngine.cpp` | `NullPointer_Injection_NoCrash` | 163-171 | `SRS-AEB-205`, `SRS-AEB-206` | `sym/test/test_Aeb_FusionEngine.cpp/NullPointer_Injection_NoCrash/` |
| `test/test_functional_scenario.py` | `reset_system` | 70-73 | - | `sym/test/test_functional_scenario.py/reset_system/` |
| `test/test_functional_scenario.py` | `_run_cycles` | 76-78 | - | `sym/test/test_functional_scenario.py/_run_cycles/` |
| `test/test_functional_scenario.py` | `test_initial_state_is_safe` | 81-89 | `SRS-AEB-102`, `SRS-AEB-103` | `sym/test/test_functional_scenario.py/test_initial_state_is_safe/` |
| `test/test_functional_scenario.py` | `test_functional_scenario_emergency_braking` | 92-120 | `SRS-AEB-102`, `SRS-AEB-103`, `SRS-AEB-303`, `SRS-AEB-401`, `SRS-AEB-402` | `sym/test/test_functional_scenario.py/test_functional_scenario_emergency_braking/` |
| `test/test_functional_scenario.py` | `test_functional_scenario_pedestrian_weight_advances_braking` | 123-143 | `SRS-AEB-305` | `sym/test/test_functional_scenario.py/test_functional_scenario_pedestrian_weight_advances_braking/` |
| `test/test_functional_scenario.py` | `test_functional_scenario_sensor_fault_failsafe` | 146-167 | `SRS-AEB-202`, `SRS-AEB-203`, `SRS-AEB-204` | `sym/test/test_functional_scenario.py/test_functional_scenario_sensor_fault_failsafe/` |
| `test/test_functional_scenario.py` | `test_functional_scenario_target_receding_no_braking` | 170-179 | `SRS-AEB-302`, `SRS-AEB-304` | `sym/test/test_functional_scenario.py/test_functional_scenario_target_receding_no_braking/` |
| `test/test_functional_scenario.py` | `test_functional_scenario_invalid_target_no_braking` | 182-190 | `SRS-AEB-302`, `SRS-AEB-304` | `sym/test/test_functional_scenario.py/test_functional_scenario_invalid_target_no_braking/` |
