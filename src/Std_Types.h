/**
 * @file    Std_Types.h
 * @brief   AUTOSAR Std_Types 최소 구현 (데모/SIL 빌드용)
 *
 * @note    실제 양산 환경에서는 MCAL 벤더가 제공하는 Std_Types.h 를 사용한다.
 *          본 파일은 호스트(x86) 상에서 단위/기능 시험 및 커버리지 계측을
 *          수행하기 위한 대체 정의이며, Platform_Types.h 의 최소 부분집합만 포함한다.
 */
#ifndef STD_TYPES_H
#define STD_TYPES_H

/* --- Platform_Types.h (AUTOSAR SWS_Platform) 부분집합 --- */
typedef unsigned char       boolean;
typedef signed char         sint8;
typedef unsigned char       uint8;
typedef signed short        sint16;
typedef unsigned short      uint16;
typedef signed long         sint32;
typedef unsigned long       uint32;
typedef float               float32;
typedef double              float64;

#ifndef TRUE
#define TRUE  ((boolean)1)
#endif

#ifndef FALSE
#define FALSE ((boolean)0)
#endif

/* --- Std_Types.h (AUTOSAR SWS_StandardTypes) 부분집합 --- */
typedef uint8 Std_ReturnType;

#define E_OK        ((Std_ReturnType)0x00U)
#define E_NOT_OK    ((Std_ReturnType)0x01U)

#endif /* STD_TYPES_H */
