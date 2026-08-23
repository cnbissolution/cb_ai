/**
 * @file    Aeb_TestHarness.c
 * @brief   SIL(Software-in-the-Loop) 기능 시험용 테스트 하네스
 *
 * Aeb_FusionEngine 을 호스트에서 구동하기 위해 센서/액추에이터 인터페이스를
 * 소프트웨어 목(mock)으로 대체하고, Python(ctypes)에서 호출할 수 있는
 * C 래퍼 함수를 export 한다.
 *
 * 빌드:
 *   gcc --coverage -fPIC -shared -o libaeb.so \
 *       src/Aeb_FusionEngine.c test/Aeb_TestHarness.c -Isrc
 *
 * @note 단위 시험(GTest)은 gmock 으로 인터페이스를 주입하므로 이 하네스를 쓰지 않는다.
 *       이 파일은 기능 시험(시계열 시나리오) 전용이다.
 */
#include "Aeb_Interfaces.h"

extern void Aeb_Init(Aeb_SystemContext* context, IRadarSensor* radar,
                     ICameraSensor* camera, IBrakeActuator* brake);
extern void Aeb_MainFunction_10ms(Aeb_SystemContext* context);

/* ---------------- Mock 상태 (시나리오 주입 지점) ---------------- */
static TargetObject s_mockRadarTarget  = { 0.0F, 0.0F, FALSE };
static TargetObject s_mockCameraTarget = { 0.0F, 0.0F, FALSE };
static boolean      s_mockPedestrian   = FALSE;
static uint8        s_mockSensorStatus = 0x00U;

/* ---------------- 관측 상태 (Assertion 지점) ---------------- */
static float32 s_brakeCommand_Pct = 0.0F;
static uint32  s_applyBrakeCallCount = 0U;
static uint32  s_releaseBrakeCallCount = 0U;

/* ---------------- Mock 인터페이스 구현 ---------------- */
static void Mock_GetRadarTarget(TargetObject* out_target)
{
    if (out_target != 0) { *out_target = s_mockRadarTarget; }
}

static uint8 Mock_GetSensorStatus(void)
{
    return s_mockSensorStatus;
}

static void Mock_GetCameraTarget(TargetObject* out_target)
{
    if (out_target != 0) { *out_target = s_mockCameraTarget; }
}

static boolean Mock_IsPedestrianDetected(void)
{
    return s_mockPedestrian;
}

static void Mock_ApplyEmergencyBrake(float32 brakeForce_Pct)
{
    s_brakeCommand_Pct = brakeForce_Pct;
    s_applyBrakeCallCount++;
}

static void Mock_ReleaseBrake(void)
{
    s_brakeCommand_Pct = 0.0F;
    s_releaseBrakeCallCount++;
}

/* ---------------- 인터페이스 인스턴스 및 컨텍스트 ---------------- */
static IRadarSensor   s_radar  = { Mock_GetRadarTarget,  Mock_GetSensorStatus };
static ICameraSensor  s_camera = { Mock_GetCameraTarget, Mock_IsPedestrianDetected };
static IBrakeActuator s_brake  = { Mock_ApplyEmergencyBrake, Mock_ReleaseBrake };

static Aeb_SystemContext s_context;

/* ================= Python(ctypes) 노출 API ================= */

void Aeb_Init_Wrapper(void)
{
    s_mockRadarTarget.Distance_M         = 0.0F;
    s_mockRadarTarget.RelativeSpeed_Kmph = 0.0F;
    s_mockRadarTarget.IsValid            = FALSE;
    s_mockCameraTarget.Distance_M         = 0.0F;
    s_mockCameraTarget.RelativeSpeed_Kmph = 0.0F;
    s_mockCameraTarget.IsValid            = FALSE;
    s_mockPedestrian        = FALSE;
    s_mockSensorStatus      = 0x00U;
    s_brakeCommand_Pct      = 0.0F;
    s_applyBrakeCallCount   = 0U;
    s_releaseBrakeCallCount = 0U;

    Aeb_Init(&s_context, &s_radar, &s_camera, &s_brake);
}

void Aeb_MainFunction_10ms_Wrapper(void)
{
    Aeb_MainFunction_10ms(&s_context);
}

/* --- 시나리오 주입 --- */
void SetMockRadarTarget(float32 distance_M, float32 relSpeed_Kmph, boolean isValid)
{
    s_mockRadarTarget.Distance_M         = distance_M;
    s_mockRadarTarget.RelativeSpeed_Kmph = relSpeed_Kmph;
    s_mockRadarTarget.IsValid            = isValid;
}

void SetMockPedestrianDetected(boolean detected)
{
    s_mockPedestrian = detected;
}

void SetMockSensorStatus(uint8 status)
{
    s_mockSensorStatus = status;
}

/* --- 결과 관측 --- */
float32 GetBrakeCommand(void)
{
    return s_brakeCommand_Pct;
}

float32 GetCalculatedTTC(void)
{
    return s_context.CalculatedTTC;
}

boolean GetSystemFaultFlag(void)
{
    return s_context.IsSystemFault;
}

uint32 GetApplyBrakeCallCount(void)
{
    return s_applyBrakeCallCount;
}

uint32 GetReleaseBrakeCallCount(void)
{
    return s_releaseBrakeCallCount;
}
