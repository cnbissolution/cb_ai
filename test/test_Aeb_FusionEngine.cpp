#include <gtest/gtest.h>
#include <gmock/gmock.h>

extern "C" {
    #include "Aeb_Interfaces.h"
    extern void Aeb_Init(Aeb_SystemContext* context, IRadarSensor* radar, ICameraSensor* camera, IBrakeActuator* brake);
    extern void Aeb_MainFunction_10ms(Aeb_SystemContext* context);
}

using ::testing::_;
using ::testing::Return;
using ::testing::SetArgPointee;
using ::testing::DoAll;

/* Mock 클래스 정의 */
class MockRadarSensor {
public:
    MOCK_METHOD(void, GetRadarTarget, (TargetObject*));
    MOCK_METHOD(uint8, GetSensorStatus, ());
};

class MockCameraSensor {
public:
    MOCK_METHOD(void, GetCameraTarget, (TargetObject*));
    MOCK_METHOD(boolean, IsPedestrianDetected, ());
};

class MockBrakeActuator {
public:
    MOCK_METHOD(void, ApplyEmergencyBrake, (float32));
    MOCK_METHOD(void, ReleaseBrake, ());
};

/* C 인터페이스 브릿지 변수 및 함수 */
MockRadarSensor* g_mockRadar = nullptr;
MockCameraSensor* g_mockCamera = nullptr;
MockBrakeActuator* g_mockBrake = nullptr;

void Adapter_GetRadarTarget(TargetObject* out) { g_mockRadar->GetRadarTarget(out); }
uint8 Adapter_GetSensorStatus() { return g_mockRadar->GetSensorStatus(); }
void Adapter_GetCameraTarget(TargetObject* out) { g_mockCamera->GetCameraTarget(out); }
boolean Adapter_IsPedestrianDetected() { return g_mockCamera->IsPedestrianDetected(); }
void Adapter_ApplyEmergencyBrake(float32 force) { g_mockBrake->ApplyEmergencyBrake(force); }
void Adapter_ReleaseBrake() { g_mockBrake->ReleaseBrake(); }

/* Test Fixture */
class AebFusionEngineTest : public ::testing::Test {
protected:
    Aeb_SystemContext context;
    IRadarSensor radarInterface;
    ICameraSensor cameraInterface;
    IBrakeActuator brakeInterface;

    MockRadarSensor mockRadar;
    MockCameraSensor mockCamera;
    MockBrakeActuator mockBrake;

    void SetUp() override {
        g_mockRadar = &mockRadar;
        g_mockCamera = &mockCamera;
        g_mockBrake = &mockBrake;

        radarInterface.GetRadarTarget = Adapter_GetRadarTarget;
        radarInterface.GetSensorStatus = Adapter_GetSensorStatus;
        cameraInterface.GetCameraTarget = Adapter_GetCameraTarget;
        cameraInterface.IsPedestrianDetected = Adapter_IsPedestrianDetected;
        brakeInterface.ApplyEmergencyBrake = Adapter_ApplyEmergencyBrake;
        brakeInterface.ReleaseBrake = Adapter_ReleaseBrake;

        Aeb_Init(&context, &radarInterface, &cameraInterface, &brakeInterface);
    }
};

/* 테스트 케이스 1: 보행자 가중치가 긴급 제동을 유발하는지 검증 [SRS-AEB-305, 401] */
TEST_F(AebFusionEngineTest, PedestrianWeight_TriggersEmergencyBrake) {
    TargetObject mockTarget = { 18.0F, -36.0F, TRUE }; // 기본 TTC = 1.8초
    
    EXPECT_CALL(mockRadar, GetSensorStatus()).WillOnce(Return(0x00U));
    EXPECT_CALL(mockRadar, GetRadarTarget(_)).WillOnce(DoAll(SetArgPointee<0>(mockTarget), Return()));
    EXPECT_CALL(mockCamera, GetCameraTarget(_)).WillOnce(Return());
    
    // 보행자 감지로 0.8 가중치 적용 (TTC = 1.44초로 하락)
    EXPECT_CALL(mockCamera, IsPedestrianDetected()).WillOnce(Return(TRUE)); 

    // 제동이 발생해야 함
    EXPECT_CALL(mockBrake, ApplyEmergencyBrake(100.0F)).Times(1);
    EXPECT_CALL(mockBrake, ReleaseBrake()).Times(0); 

    Aeb_MainFunction_10ms(&context);
    EXPECT_FLOAT_EQ(context.CalculatedTTC, 1.44F);
}

/* 테스트 케이스 2: 보행자가 없을 경우 제동 미발생 검증 */
TEST_F(AebFusionEngineTest, NoPedestrian_TtcAboveThreshold_ReleasesBrake) {
    TargetObject mockTarget = { 18.0F, -36.0F, TRUE }; // 기본 TTC = 1.8초
    
    EXPECT_CALL(mockRadar, GetSensorStatus()).WillOnce(Return(0x00U));
    EXPECT_CALL(mockRadar, GetRadarTarget(_)).WillOnce(DoAll(SetArgPointee<0>(mockTarget), Return()));
    EXPECT_CALL(mockCamera, GetCameraTarget(_)).WillOnce(Return());
    EXPECT_CALL(mockCamera, IsPedestrianDetected()).WillOnce(Return(FALSE)); 

    // 임계값(1.5초) 이상이므로 제동 미발생
    EXPECT_CALL(mockBrake, ApplyEmergencyBrake(_)).Times(0);
    EXPECT_CALL(mockBrake, ReleaseBrake()).Times(1);

    Aeb_MainFunction_10ms(&context);
    EXPECT_FLOAT_EQ(context.CalculatedTTC, 1.8F);
}

/* 테스트 케이스 3: 0으로 나누기 예외 방어 [SRS-AEB-302] */
TEST_F(AebFusionEngineTest, CalculateTTC_DivideByZero_Prevention) {
    TargetObject mockTarget = { 10.0F, -0.001F, TRUE }; // 속도가 0에 근접
    
    EXPECT_CALL(mockRadar, GetSensorStatus()).WillOnce(Return(0x00U));
    EXPECT_CALL(mockRadar, GetRadarTarget(_)).WillOnce(DoAll(SetArgPointee<0>(mockTarget), Return()));
    EXPECT_CALL(mockCamera, IsPedestrianDetected()).WillOnce(Return(FALSE));

    EXPECT_CALL(mockBrake, ApplyEmergencyBrake(_)).Times(0);
    EXPECT_CALL(mockBrake, ReleaseBrake()).Times(1);

    Aeb_MainFunction_10ms(&context);
    
    // 계산이 스킵되고 안전 기본값 유지
    EXPECT_FLOAT_EQ(context.CalculatedTTC, 999.0F);
}

/* 테스트 케이스 4: 널 포인터 주입 시 크래시 방어 */
TEST_F(AebFusionEngineTest, NullPointer_Injection_NoCrash) {
    // 함수 포인터를 고의로 파괴
    radarInterface.GetSensorStatus = nullptr;
    
    // Segmentation Fault 없이 안전하게 Return 되는지 확인
    EXPECT_NO_FATAL_FAILURE({
        Aeb_MainFunction_10ms(&context);
    });
}
