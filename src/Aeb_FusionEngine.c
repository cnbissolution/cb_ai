#include "Aeb_Interfaces.h"

#define AEB_TTC_CRITICAL_SEC      (1.5F)
#define AEB_TTC_SAFE_DEFAULT      (999.0F)
#define AEB_PEDESTRIAN_WEIGHT     (0.8F)
#define AEB_MAX_BRAKE_FORCE_PCT   (100.0F)
#define AEB_REL_SPEED_EPSILON_MPS (0.01F) 
#define AEB_KMPH_TO_MPS(kmph)     ((kmph) / 3.6F)
#define NULL_PTR                  ((void*)0)

/* AEB 초기화 */
void Aeb_Init(Aeb_SystemContext* context, IRadarSensor* radar, ICameraSensor* camera, IBrakeActuator* brake) 
{
    if (context != NULL_PTR) {
        context->Radar = radar;
        context->Camera = camera;
        context->Brake = brake;
        context->IsSystemFault = FALSE;
        context->CalculatedTTC = AEB_TTC_SAFE_DEFAULT;
    }
}

/* 내부 TTC 계산 로직 (0으로 나누기 방어 적용) */
static float32 CalculateTTC(const TargetObject* target) 
{
    float32 ttc = AEB_TTC_SAFE_DEFAULT;
    float32 relSpeed_Mps = 0.0F;

    if (target != NULL_PTR) {
        if ((target->IsValid == TRUE) && (target->RelativeSpeed_Kmph < -0.5F)) {
            relSpeed_Mps = AEB_KMPH_TO_MPS(target->RelativeSpeed_Kmph * -1.0F);
            
            /* Divide by Zero 방어 */
            if (relSpeed_Mps > AEB_REL_SPEED_EPSILON_MPS) {
                ttc = target->Distance_M / relSpeed_Mps;
            }
        }
    }
    return ttc;
}

/* 메인 제어 루프 */
void Aeb_MainFunction_10ms(Aeb_SystemContext* context) 
{
    TargetObject radarTarget = {0.0F, 0.0F, FALSE};
    TargetObject cameraTarget = {0.0F, 0.0F, FALSE};
    boolean isPedestrian = FALSE;
    uint8 sensorStatus = 0xFFU;

    /* 1. 최상위 및 인터페이스 객체 널 포인터 체크 */
    if ((context == NULL_PTR) || (context->Radar == NULL_PTR) || 
        (context->Camera == NULL_PTR) || (context->Brake == NULL_PTR)) {
        return; 
    }

    /* 2. 센서 결함 점검 */
    if (context->Radar->GetSensorStatus != NULL_PTR) {
        sensorStatus = context->Radar->GetSensorStatus();
    }

    if (sensorStatus != 0x00U) {
        context->IsSystemFault = TRUE;
        if (context->Brake->ReleaseBrake != NULL_PTR) {
            context->Brake->ReleaseBrake();
        }
        return;
    }

    /* 3. 데이터 획득 */
    if (context->Radar->GetRadarTarget != NULL_PTR) {
        context->Radar->GetRadarTarget(&radarTarget);
    }
    
    /* 4. TTC 계산 및 가중치 반영 */
    context->CalculatedTTC = CalculateTTC(&radarTarget);
    
    if (context->Camera->IsPedestrianDetected != NULL_PTR) {
        isPedestrian = context->Camera->IsPedestrianDetected();
    }
    
    if (isPedestrian == TRUE) {
        context->CalculatedTTC *= AEB_PEDESTRIAN_WEIGHT;
    }

    /* 5. 액추에이터 제어 (TTC 임계값 비교) */
    if (context->CalculatedTTC < AEB_TTC_CRITICAL_SEC) {
        if (context->Brake->ApplyEmergencyBrake != NULL_PTR) {
            context->Brake->ApplyEmergencyBrake(AEB_MAX_BRAKE_FORCE_PCT);
        }
    } else {
        if (context->Brake->ReleaseBrake != NULL_PTR) {
            context->Brake->ReleaseBrake();
        }
    }
}
