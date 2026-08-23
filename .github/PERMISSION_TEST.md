# 이 파일은 삭제해도 된다

원래 `.github` 디렉토리 쓰기 권한을 확인하려고 만든 probe 였고,
그 다음에는 워크플로 파일을 옮기라는 안내를 담고 있었다.

**두 용도 모두 끝났다.** 파이프라인은 이미
[`.github/workflows/cicd-ct.yml`](workflows/cicd-ct.yml) 에 정상 배치되어 있다.

```bash
git rm ci/cicd-ct.yml .github/PERMISSION_TEST.md
git commit -m "chore: 이동 완료된 임시 파일 제거"
git push
```
