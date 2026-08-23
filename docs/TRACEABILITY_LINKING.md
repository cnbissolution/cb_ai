# 추적성 링크 직계 — 안 끊어지는 코드 링크 만들기

## 반증된 문제

이 문서의 이전 버전은 코드 링크를 이러게 썼다.

```
SRS-AEB-303  →  src/Aeb_FusionEngine.c:35
```

이 링크는 **주석 한 줄만 추가해도 틀린 숫자가 된다.**
이 프로젝트에서 `@req` 추적 주석을 넣자 `CalculateTTC` 의 나눗셈 라인이
**35 → 50** 으로 밀렸다. 요구사항 15건의 라인 추적이 한 번에 전부 무효화됐다.

ASPICE 심사에서 추적성 링크가 엉뚱한 코드를 가리키는 것은 링크가 없는 것보다 나쁘다.

## 해법

**심볼 이름 기준의 안정적인 URL** 을 만들고, 라인 번호는 CI 가 매번 다시 계산한다.

```
ALM 에 저장하는 것 (영구 보존):
  https://cnbissolution.github.io/cb_ai/sym/src/Aeb_FusionEngine.c/CalculateTTC/
  https://cnbissolution.github.io/cb_ai/req/SRS-AEB-303/

CI 가 매 밑드마다 갱슱하는 것:
  → https://github.com/cnbissolution/cb_ai/blob/main/src/Aeb_FusionEngine.c#L36-L55
```

코드가 이동하면 리다이렉트 대상만 바뀐다. ALM 에 저장한 URL 은 손대지 않는다.

## 두 가지 링크 형태

| 형태 | URL | 무엇으로 가는가 | 어디에 쓰는가 |
|---|---|---|---|
| 심볼 링크 | `/sym/<경로>/<심볼>/` | GitHub blob 의 해당 함수 라인 범위 | SDD 의 설계 요소 → 구현 |
| 요구사항 링크 | `/req/<요구사항ID>/` | 구현·검증 위치를 모은 랜딩 페이지 | Codebeamer 요구사항 항목 → 코드 |

요구사항 링크가 더 유용하다. 한 요구사항이 여러 곳에서 구현·검증되는 경우
(예: `SRS-AEB-305` 는 구현 1곳 + 검증 3곳) 랜딩 페이지가 전부 모아 보여준다.

## 동작 방식

```
1. 소스에 추적 주석                    2. CI 가 인덱싱               3. Pages 배포
   ┌───────────────────────┐          ┌────────────────┐        ┌─────────────┐
   │ /**                    │          │ ctags/정규식으로  │        │ /sym/.../    │
   │  * @req SRS-AEB-303    │  ─────► │ 함수 라인 범위    │ ─────► │ /req/.../    │
   │  */                    │          │ + @req 태그 파싱  │        │ (리다이렉트) │
   │ static float32         │          └────────────────┘        └─────────────┘
   │ CalculateTTC(...)      │                   │                         │
   └───────────────────────┘                   ▼                         ▼
                                   redirects_generated.json      Codebeamer 가 저장
                                   req_index.json                하는 URL
```

### 구성 요소

| 파일 | 역할 |
|---|---|
| `Doxyfile` | 소스 브라우저 사이트 생성. `@req`/`@verifies` 를 문서 섹션으로 렌더링 |
| `scripts/build_symbol_map.py` | 함수 라인 범위 + 추적 주석 파싱 → 두 JSON 산출 |
| `scripts/generate_redirects.py` | `sym/`, `req/` 리다이렉트 페이지 생성 |
| `.github/workflows/pages.yml` | 위 3개를 실행하고 GitHub Pages 로 배포 |

`build_symbol_map.py` 는 universal-ctags 가 있으면 쓰고, 없으면 정규식으로 대습한다.
CI 에는 ctags 를 설치하지만 로컴(Windows 등)에서도 그냥 돌아가야 하기 때별이다.

## 소스 주석 귬칙

```c
/**
 * @brief 내부 TTC 계산 로직
 *
 * @req SRS-AEB-302  유효하고 -0.5 km/h 미만으로 접근하는 타겟만 계산
 * @req SRS-AEB-303  TTC = 거리(m) / 상대속도(m/s)
 */
static float32 CalculateTTC(const TargetObject* target)
```

테스트에는 `@verifies` 를 쓴다.

```cpp
/**
 * @verifies SRS-AEB-305
 * @verifies SRS-AEB-401
 */
TEST_F(AebFusionEngineTest, PedestrianWeight_TriggersEmergencyBrake) {
```

| 태그 | 의밌 | 붙이는 곳 |
|---|---|---|
| `@req` | 이 코드가 요구사항을 **구현**한다 | `src/` 의 함수 |
| `@verifies` | 이 테스트가 요구사항을 **검증**한다 | `test/` 의 테스트 케이스 |
| `@satisfies` | 상위 요구사항을 **충족**한다 | 필요 시 |

함수 앞 문서 바색과 함수 밑밥 안쪽 주석 모드에서 인식된다.

## 부수 효과: 추적성 갭이 자동으로 드러난다

인덱스가 구현(`@req`)과 검증(`@verifies`)을 양쪽에서 모으므로, 한쪽만 있는 요구사항이
바로 보인다. 손으로 관리하는 매트릭스에서는 놓치기 쉬운 것들이다.

| 요구사항 | 갭 | 의밌 |
|---|---|---|
| `SRS-AEB-101` | 검증 없음 | 구현은 있는데 이를 검증하는 테스트가 없다 |
| `SRS-AEB-201` | 검증 없음 | 10ms 주기는 단위시험으로 검증 불가 (설계 리뷰 대상) |
| `SRS-AEB-205`, `SRS-AEB-206` | 고아 테스트 | 테스트는 있는데 요구사항이 승인 안 됐다 |
| `SRS-AEB-306` | 검증 없음 | 도달 불가 코드라 검증 자체가 성립 안 한다 (REVIEW.md D-2) |

CI 는 이 갭을 `::warning` 으로 올려 Actions 요약에 표시한다.

## Codebeamer 연동

요구사항 트래커에 URL 필드(또는 Wiki 링크)를 하나 두고 요구사항 링크를 저장한다.

| Codebeamer 필드 | 값 |
|---|---|
| Code Link (URL) | `https://cnbissolution.github.io/cb_ai/req/SRS-AEB-305/` |
| Design Ref | SDD 8절 |

`scripts/upload_to_codebeamer.py` 로 Test Run 을 만들 때 이 링크를 설명에 함께 넣으면,
Test Run → 요구사항 → 코드가 한 번에 연결된다.

## 로컴 실행

```bash
python3 scripts/build_symbol_map.py
python3 scripts/generate_redirects.py
```

Doxygen 없이도 리다이렉트만 단독 생성된다 (`docs_build/html/` 아래).
Doxygen 까지 포함한 전잴 사이트는 CI 에서 만들어진다.

## 한계

- **함수 이름을 바꾸면 링크가 깨진다.** 심볼 이름이 키이기 때별이다. 라인 이동보다는
  훨씬 드므지만, 리네임 시에는 ALM 링크도 갱슱해야 한다.
- 정적 변수, 매크로, 구조체 필드는 인덱싱하지 않는다. 함수와 테스트 케이스만 대상이다.
- 오버로드된 C++ 함수는 이름이 같으면 마지막 것만 남는다. 현재 프로젝트는 C 위주라 무해하다.
