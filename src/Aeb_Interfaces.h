#ifndef AEB_INTERFACES_H
#define AEB_INTERFACES_H

#include "Std_Types.h"

/* 데이터 클래스 */
typedef struct {
    float32 Distance_M;
    float32 RelativeSpeed_Kmph;
    boolean IsValid;
} TargetObject;

/* 센서 및 액추에이터 인터페이스 (함수 포인터) */
typedef struct {
    void (*GetRadarTarget)(TargetObject* out_target);
    uint8 (*GetSensorStatus)(void);
} IRadarSensor;

typedef struct {
    void (*GetCameraTarget)(TargetObject* out_target);
    boolean (*IsPedestrianDetected)(void);
} ICameraSensor;

typedef struct {
    void (*ApplyEmergencyBrake)(float32 brakeForce_Pct);
    void (*ReleaseBrake)(void);
} IBrakeActuator;

/* AEB 메인 컨텍스트 */
typedef struct {
    IRadarSensor*   Radar;
    ICameraSensor*  Camera;
    IBrakeActuator* Brake;
    boolean         IsSystemFault;
    float32         CalculatedTTC;
} Aeb_SystemContext;

#endif /* AEB_INTERFACES_H */
