# 워크플로 배치 안내

> 이 파일은 원래 `.github` 디렉토리 쓰기 권한을 확인하려고 만든 probe 였다.
> 삭제하거나 `.github/README.md` 로 이름을 바꿔도 무방하다.

## 해야 할 일

파이프라인 정의는 현재 `ci/cicd-ct.yml` 에 있다.
GitHub Actions 가 인식하려면 `.github/workflows/` 아래로 옮겨야 한다.

```bash
git mv ci/cicd-ct.yml .github/workflows/cicd-ct.yml
```

## 왜 처음부터 거기에 두지 않았나

최초 커밋에 사용한 토큰에 `workflow` 스코프가 없어
`.github/workflows/` 경로에 직접 쓸 수 없었다 (`.github/` 자체는 가능).

GitHub API 는 `workflow` 스코프 없는 토큰이 워크플로 파일을 생성·수정하려 하면
차단한다. 로컬에서 `git mv` 후 push 하거나, `workflow` 스코프를 포함한 토큰으로
다시 시도하면 해결된다.

## 이동 후 확인

- Actions 탭에 "AEB CI/CD/CT Pipeline" 이 나타난다
- `workflow_dispatch` 로 수동 실행이 가능해진다
- `repository_dispatch` 의 `types` (`codebeamer-test-request`,
  `codebeamer-requirement-approved`) 가 등록되어
  `scripts/cb_trigger_ci.py` 호출이 422 없이 통과한다
