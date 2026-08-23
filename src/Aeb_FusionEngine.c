#include "Aeb_Interfaces.h"

#define AEB_TTC_CRITICAL_SEC      (1.5F)
#define AEB_TTC_SAFE_DEFAULT      (999.0F)
#define AEB_PEDESTRIAN_WEIGHT     (0.8F)
#define AEB_MAX_BRAKE_FORCE_PCT   (100.0F)
#define AEB_REL_SPEED_EPSILON_MPS (0.01F) 
#define AEB_KMPH_TO_MPS(kmph)     ((kmph) / 3.6F)
#define NULL_PTR                  ((void*)0)

/**
 * @brief AEB 초기화 — 인터페이스 주입 및 안전 기본값 설정
 *
 * @req SRS-AEB-101  레이더/카메라/제동 인터페이스 포인터 검증 및 할당
 * @req SRS-AEB-102  내부 결함 상태를 FALSE 로 설정
 * @req SRS-AEB-103  TTC 를 안전 기본값(999.0초)으로 설정
 */
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

/**
 * @brief 내부 TTC 계산 로직 (0으로 나누기 방어 적용)
 *
 * @req SRS-AEB-302  유효하고 -0.5 km/h 미만으로 접근하는 타겟만 계산
 * @req SRS-AEB-303  TTC = 거리(m) / 상대속도(m/s)
 * @req SRS-AEB-304  무효/이탈 타겟은 999.0초 유지
 */
static float32 CalculateTTC(const TargetObject* target)
{
    float32 ttc = AEB_TTC_SAFE_DEFAULT;
    float32 relSpeed_Mps = 0.0F;

    if (target != NULL_PTR) {
        if ((target->IsValid == TRUE) && (target->RelativeSpeed_Kmph < -0.5F)) {
            relSpeed_Mps = AEB_KMPH_TO_MPS(target->RelativeSpeed_Kmph * -1.0F);
            
            /* Divide by Zero 방어
             * @req SRS-AEB-306 (보류)
             * 상위 가드(-0.5 km/h)로 인해 relSpeed_Mps 는 항상 0.1389 이상이므로
             * 이 조건은 항상 참이고 else 경로는 도달 불가하다. REVIEW.md D-2 참조. */
            if (relSpeed_Mps > AEB_REL_SPEED_EPSILON_MPS) {
                ttc = target->Distance_M / relSpeed_Mps;
            }
        }
    }
    return ttc;
}

/**
 * @brief 10ms 주기 메인 제어 루프
 *
 * @req SRS-AEB-201  10ms 주기 실행 (OS 스케줄러가 호출)
 * @req SRS-AEB-202  매 주기 센서 상태 확인
 * @req SRS-AEB-203  비정상 상태 시 결함 플래그 설정
 * @req SRS-AEB-204  결함 시 제동 해제 후 즉시 종료
 * @req SRS-AEB-301  레이더/카메라 타겟 수집
 *                   (주의: 카메라 타겟 수집 미구현 — REVIEW.md D-1)
 * @req SRS-AEB-305  보행자 감지 시 TTC 에 0.8 가중치 적용
 * @req SRS-AEB-401  TTC < 1.5초 시 100% 긴급 제동
 * @req SRS-AEB-402  그 외에는 제동 해제
 */
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
