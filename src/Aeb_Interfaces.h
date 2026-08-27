#ifndef AEB_INTERFACES_H
#define AEB_INTERFACES_H

#include "Std_Types.h"

/**
 * @brief 전방 위협 타겟
 *
 * @unit SCS-AI-001 -> SDD-AEB-201
 * @verified_by SCS-AF-002  TTC 계산이 이 구조체를 읽는다
 */
typedef struct {
    float32 Distance_M;
    float32 RelativeSpeed_Kmph;
    boolean IsValid;
} TargetObject;

/**
 * @brief 레이더 센서 인터페이스
 *
 * @unit SCS-AI-002 -> SDD-AEB-401
 * @verified_by SCS-AF-001  초기화가 이 인터페이스를 주입·검증한다
 */
typedef struct {
    void (*GetRadarTarget)(TargetObject* out_target);
    uint8 (*GetSensorStatus)(void);
} IRadarSensor;

/**
 * @brief 카메라 센서 인터페이스
 *
 * @unit SCS-AI-003 -> SDD-AEB-402
 * @verified_by SCS-AF-001  초기화가 이 인터페이스를 주입·검증한다
 */
typedef struct {
    void (*GetCameraTarget)(TargetObject* out_target);
    boolean (*IsPedestrianDetected)(void);
} ICameraSensor;

/**
 * @brief 제동 액추에이터 인터페이스
 *
 * @unit SCS-AI-004 -> SDD-AEB-403
 * @verified_by SCS-AF-001  초기화가 이 인터페이스를 주입·검증한다
 */
typedef struct {
    void (*ApplyEmergencyBrake)(float32 brakeForce_Pct);
    void (*ReleaseBrake)(void);
} IBrakeActuator;

/**
 * @brief AEB 메인 컨텍스트 — 주입된 인터페이스와 주기 간 상태
 *
 * @unit SCS-AI-005 -> SDD-AEB-202
 * @verified_by SCS-AF-001  초기화가 이 컨텍스트를 설정한다
 */
typedef struct {
    IRadarSensor*   Radar;
    ICameraSensor*  Camera;
    IBrakeActuator* Brake;
    boolean         IsSystemFault;
    float32         CalculatedTTC;
} Aeb_SystemContext;

#endif /* AEB_INTERFACES_H */