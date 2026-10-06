# GitHub 유지 관리

저장소: https://github.com/zno5/gun-nac-ko

한국어 번역표와 도구·문서를 Git에 보관하고, IPS 패치는 ZIP으로 Releases에 배포합니다. ROM·폰트 원본·추출 그래픽·캡처는 커밋하지 않습니다. 자체 도구 코드·기술 문서는 [MIT 라이선스](../LICENSE)를 따르며 적용 범위는 [권리 안내](RIGHTS.ko.md)를 확인하세요.

## 수정과 게시

```sh
python3 tools/check_sources.py
python3 tools/audit_public.py
python3 tools/build.py --rom "/path/to/Gun Nac (Japan).nes"
git add .
python3 tools/audit_public.py --staged
git commit -m "Describe the change"
git push
```

새 소스 파일은 `publish_manifest.json`에도 등록합니다. 최초 체크아웃에서는 `git config core.hooksPath .githooks`로 커밋 전 검사를 켤 수 있습니다. CI는 ROM 없이 소스만 검사합니다.

## 릴리스

빌드된 IPS, 적용 안내, 사용한 폰트의 라이선스·출처를 ZIP에 넣습니다. 원본/수정 ROM, 게임 캡처, 폰트 원본을 넣지 않습니다. ZIP 내부 목록과 체크섬을 확인하고 검사 범위 및 미검증 항목을 릴리스 노트에 기록합니다. 완주 검증 전에는 사전 릴리스를 사용합니다.

```sh
gh release create VERSION PATCH.zip SHA256SUMS.txt --prerelease --title "Gun Nac 한국어 패치 VERSION" --notes-file release-notes.md
```

계정 인증은 `gh auth login`, 상태 확인은 `gh auth status`입니다. 액세스 토큰을 파일이나 문서에 붙이지 않습니다.
