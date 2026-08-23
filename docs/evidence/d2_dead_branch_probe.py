"""
D-2 실측 검증 스크립트 — Epsilon 방어 로직이 도달 불가(dead branch)임을 증명한다.

src/Aeb_FusionEngine.c 의 두 조건을 비교한다.
  :30  if ((target->IsValid == TRUE) && (target->RelativeSpeed_Kmph < -0.5F))   <- 상위 가드
  :34      if (relSpeed_Mps > AEB_REL_SPEED_EPSILON_MPS)                        <- Epsilon 검사

상위 가드를 통과하려면 |RelativeSpeed_Kmph| > 0.5 여야 하므로,
:34 지점의 relSpeed_Mps 는 항상 0.5/3.6 = 0.1389 m/s 를 초과한다.
Epsilon(0.01 m/s)의 약 14배이므로 else 경로는 어떤 입력으로도 실행되지 않는다.

빌드 및 실행:
  mkdir -p build
  gcc -std=c99 -Isrc -c src/Aeb_FusionEngine.c -o build/Aeb_FusionEngine.o
  gcc -std=c99 -Isrc -c test/Aeb_TestHarness.c -o build/Aeb_TestHarness.o
  gcc -shared -o libaeb.so build/*.o
  AEB_LIB_PATH=./libaeb.so python3 docs/evidence/d2_dead_branch_probe.py
"""
import ctypes
import os
import sys

LIB_PATH = os.environ.get("AEB_LIB_PATH", os.path.join(os.getcwd(), "libaeb.so"))

if not os.path.exists(LIB_PATH):
    sys.exit("라이브러리를 찾을 수 없습니다: %s\n"
             "AEB_LIB_PATH 환경변수로 경로를 지정하거나 먼저 빌드하십시오." % LIB_PATH)

aeb = ctypes.CDLL(LIB_PATH)
aeb.SetMockRadarTarget.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_ubyte]
aeb.GetCalculatedTTC.restype = ctypes.c_float
aeb.GetBrakeCommand.restype = ctypes.c_float

EPSILON_MPS = 0.01   # AEB_REL_SPEED_EPSILON_MPS
GUARD_KMPH = -0.5    # 상위 가드 임계값

print("  relSpeed(km/h) |  relSpeed(m/s) |  TTC     | epsilon(0.01) 분기 진입?")
print("  " + "-" * 70)

# -0.5 km/h 가드 경계 주변을 촘촘히 스윕
for kmph in [-0.4, -0.49, -0.5, -0.500001, -0.51, -0.6, -1.0, -3.6, -36.0]:
    aeb.Aeb_Init_Wrapper()
    aeb.SetMockRadarTarget(10.0, kmph, 1)
    aeb.Aeb_MainFunction_10ms_Wrapper()

    ttc = aeb.GetCalculatedTTC()
    mps = abs(kmph) / 3.6
    guard_passed = kmph < GUARD_KMPH
    # 가드를 통과했는데 TTC 가 999 라면 epsilon else 분기를 탄 것
    took_else = guard_passed and abs(ttc - 999.0) < 1e-3

    if took_else:
        verdict = "YES(도달!)"
    elif guard_passed:
        verdict = "no (나눗셈 수행)"
    else:
        verdict = "가드에서 차단"

    print("  %14.6f | %14.6f | %8.3f | %s" % (kmph, mps, ttc, verdict))

min_mps = abs(GUARD_KMPH) / 3.6
print()
print("  epsilon 임계값        : %s m/s" % EPSILON_MPS)
print("  가드 통과 최소 |m/s| : %.6f  (= %s/3.6)" % (min_mps, abs(GUARD_KMPH)))
print("  -> 가드를 통과한 모든 입력의 분모가 epsilon의 %.1f배 이상" % (min_mps / EPSILON_MPS))
print("  -> relSpeed_Mps > %s 은 항상 참. else 분기 도달 불가 (dead branch) 확정" % EPSILON_MPS)
