"""
[SWE.4 / 기능 시험] AEB 센서 퓨전 엔진 SIL(Software-in-the-Loop) 시나리오 테스트

계측 빌드된 공유 라이브러리(libaeb.so)를 ctypes 로 로드하여, 10ms 태스크를
시간 순서대로 반복 호출함으로써 '시계열 주행 상황'에서의 시스템 거동을 검증한다.

단위 시험(GTest)과의 차이:
  - 단위 시험: 함수 1회 호출에 대한 고립 검증 (gmock 주입)
  - 기능 시험: 다수 주기에 걸친 상태 변화 및 액추에이터 명령 이력 검증 (C 하네스)

빌드 전제:
  gcc --coverage -fPIC -shared -o libaeb.so src/Aeb_FusionEngine.c test/Aeb_TestHarness.c -Isrc

실행:
  pytest test/test_functional_scenario.py --junitxml=functional_report.xml
"""
import ctypes
import os

import pytest

# --- 라이브러리 로드 ---------------------------------------------------------
_LIB_PATH = os.environ.get("AEB_LIB_PATH", os.path.join(os.getcwd(), "libaeb.so"))

if not os.path.exists(_LIB_PATH):
    pytest.skip(
        f"libaeb.so 를 찾을 수 없습니다: {_LIB_PATH}. "
        "먼저 계측 빌드를 수행하십시오.",
        allow_module_level=True,
    )

aeb = ctypes.CDLL(_LIB_PATH)

# --- 시그니처 선언 (필수: 기본 restype 은 int 이므로 float 반환값이 깨진다) ----
aeb.Aeb_Init_Wrapper.argtypes = []
aeb.Aeb_Init_Wrapper.restype = None

aeb.Aeb_MainFunction_10ms_Wrapper.argtypes = []
aeb.Aeb_MainFunction_10ms_Wrapper.restype = None

aeb.SetMockRadarTarget.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_ubyte]
aeb.SetMockRadarTarget.restype = None

aeb.SetMockPedestrianDetected.argtypes = [ctypes.c_ubyte]
aeb.SetMockPedestrianDetected.restype = None

aeb.SetMockSensorStatus.argtypes = [ctypes.c_ubyte]
aeb.SetMockSensorStatus.restype = None

aeb.GetBrakeCommand.argtypes = []
aeb.GetBrakeCommand.restype = ctypes.c_float

aeb.GetCalculatedTTC.argtypes = []
aeb.GetCalculatedTTC.restype = ctypes.c_float

aeb.GetSystemFaultFlag.argtypes = []
aeb.GetSystemFaultFlag.restype = ctypes.c_ubyte

aeb.GetApplyBrakeCallCount.argtypes = []
aeb.GetApplyBrakeCallCount.restype = ctypes.c_uint32

aeb.GetReleaseBrakeCallCount.argtypes = []
aeb.GetReleaseBrakeCallCount.restype = ctypes.c_uint32

TRUE, FALSE = 1, 0
CYCLE_COUNT_100MS = 10  # 10ms 주기 x 10회


@pytest.fixture(autouse=True)
def reset_system():
    """매 테스트 시작 시 하네스 상태 및 AEB 컨텍스트 초기화."""
    aeb.Aeb_Init_Wrapper()
    yield


def _run_cycles(count=CYCLE_COUNT_100MS):
    for _ in range(count):
        aeb.Aeb_MainFunction_10ms_Wrapper()


def test_initial_state_is_safe():
    """초기 상태에서 TTC 는 안전 기본값이고 제동 명령이 없어야 한다.

    @verifies SRS-AEB-102
    @verifies SRS-AEB-103
    """
    assert aeb.GetCalculatedTTC() == pytest.approx(999.0)
    assert aeb.GetBrakeCommand() == pytest.approx(0.0)
    assert aeb.GetSystemFaultFlag() == FALSE


def test_functional_scenario_emergency_braking():
    """
    시계열 접근 시나리오

    @verifies SRS-AEB-303
    @verifies SRS-AEB-401
    @verifies SRS-AEB-402

    [시나리오] 60km/h 주행 중 전방 정지 차량 발견 (상대속도 -60km/h = -16.667m/s)
      1. 초기 상태          : 타겟 없음        -> TTC 999.0s, 미제동
      2. 0~100ms 구간       : 30m 앞 정지 차량 -> TTC 1.8s (>= 1.5s) -> 미제동
      3. 100~200ms 구간     : 20m 로 접근      -> TTC 1.2s (<  1.5s) -> 100% 긴급 제동
    """
    # 1단계: 타겟 없음
    _run_cycles()
    assert aeb.GetBrakeCommand() == pytest.approx(0.0)

    # 2단계: 30m / -60km/h -> TTC 1.8s
    aeb.SetMockRadarTarget(30.0, -60.0, TRUE)
    _run_cycles()
    assert aeb.GetCalculatedTTC() == pytest.approx(1.8, abs=1e-3)
    assert aeb.GetBrakeCommand() == pytest.approx(0.0), "TTC 1.8s 에서는 제동하지 않아야 한다"

    # 3단계: 20m / -60km/h -> TTC 1.2s -> 긴급 제동
    aeb.SetMockRadarTarget(20.0, -60.0, TRUE)
    _run_cycles()
    assert aeb.GetCalculatedTTC() == pytest.approx(1.2, abs=1e-3)
    assert aeb.GetBrakeCommand() == pytest.approx(100.0), "TTC 1.2s 에서는 100% 제동해야 한다"
    assert aeb.GetApplyBrakeCallCount() == CYCLE_COUNT_100MS


def test_functional_scenario_pedestrian_weight_advances_braking():
    """
    보행자 가중치가 제동 시점을 앞당기는지 시계열로 검증

    @verifies SRS-AEB-305

    동일한 18m / -36km/h(-10m/s) 조건에서
      - 보행자 미감지: TTC 1.8s  -> 미제동
      - 보행자 감지  : TTC 1.44s -> 제동 (임계값 1.5s 역전)
    """
    aeb.SetMockRadarTarget(18.0, -36.0, TRUE)
    aeb.SetMockPedestrianDetected(FALSE)
    _run_cycles()
    assert aeb.GetCalculatedTTC() == pytest.approx(1.8, abs=1e-3)
    assert aeb.GetBrakeCommand() == pytest.approx(0.0)

    # 동일 거리/속도인데 보행자만 감지되기 시작 -> 제동 발동
    aeb.SetMockPedestrianDetected(TRUE)
    _run_cycles()
    assert aeb.GetCalculatedTTC() == pytest.approx(1.44, abs=1e-3)
    assert aeb.GetBrakeCommand() == pytest.approx(100.0)


def test_functional_scenario_sensor_fault_failsafe():
    """
    주행 중 센서 결함 발생 시 페일세이프

    @verifies SRS-AEB-202
    @verifies SRS-AEB-203
    @verifies SRS-AEB-204

    긴급 제동 중이던 상황에서 레이더 결함(0x01)이 발생하면
    결함 플래그가 설정되고 제동이 해제되어야 한다.
    """
    # 제동 중 상태로 진입
    aeb.SetMockRadarTarget(20.0, -60.0, TRUE)
    _run_cycles()
    assert aeb.GetBrakeCommand() == pytest.approx(100.0)
    assert aeb.GetSystemFaultFlag() == FALSE

    # 주행 중 레이더 결함 발생
    aeb.SetMockSensorStatus(0x01)
    _run_cycles()
    assert aeb.GetSystemFaultFlag() == TRUE, "센서 결함 시 결함 플래그가 설정되어야 한다"
    assert aeb.GetBrakeCommand() == pytest.approx(0.0), "결함 시 제동을 해제해야 한다"


def test_functional_scenario_target_receding_no_braking():
    """멀어지는 타겟은 TTC 계산 대상이 아니다.

    @verifies SRS-AEB-302
    @verifies SRS-AEB-304
    """
    aeb.SetMockRadarTarget(10.0, +20.0, TRUE)  # 양수 상대속도 = 멀어짐
    _run_cycles()
    assert aeb.GetCalculatedTTC() == pytest.approx(999.0)
    assert aeb.GetBrakeCommand() == pytest.approx(0.0)


def test_functional_scenario_invalid_target_no_braking():
    """IsValid=FALSE 인 타겟은 무시되어야 한다.

    @verifies SRS-AEB-302
    """
    aeb.SetMockRadarTarget(5.0, -80.0, FALSE)  # 매우 위험해 보이지만 무효 데이터
    _run_cycles()
    assert aeb.GetCalculatedTTC() == pytest.approx(999.0)
    assert aeb.GetBrakeCommand() == pytest.approx(0.0)
