# Gun Nac 일본판 한국어화 소스

일본판 패미콤 **Gun Nac**을 기반으로 한 한국어화 작업의 편집 가능한 번역표, 로컬 빌드 도구, 검증 도구와 연구 기록입니다. 다른 작업자가 자신의 원본 ROM과 공식 배포 폰트를 준비해 번역을 고치고 IPS 패치를 재생성할 수 있도록 정리했습니다.

**이 저장소에는 ROM, 폰트 파일, 게임 화면, 추출 그래픽, 일본어 대사 전문, 완성 IPS가 없습니다.** 게임과 외부 폰트의 권리는 해당 권리자에게 있으며, 이 프로젝트는 공식 번역판이 아닙니다. 압축한 IPS와 적용 안내는 [Releases](https://github.com/zno5/gun-nac-ko/releases)에서 제공합니다. [공개 범위·권리 안내](docs/RIGHTS.ko.md)

## 시작하기

필수 도구는 **Python 3.10 이상과 Git**입니다. 빌드에는 별도 pip 패키지, C 컴파일러, 어셈블러, rom-tools가 필요하지 않습니다. 검증 환경은 macOS의 Python 3.14.7 / Mesen libretro 0.9.9이며, 다른 환경은 아래 문서를 확인하세요.

```sh
python3 tools/check_sources.py
python3 tools/fetch_fonts.py
python3 tools/build.py --rom "/path/to/Gun Nac (Japan).nes" --check-reference
```

폰트 도구는 공식 저장소의 고정 버전만 받아 해시를 검사합니다. **ROM은 다운로드하지 않습니다.** 생성물은 Git에서 제외되는 `build/`에만 놓입니다.

- 로컬 IPS: `build/stage_patch/gun_nac_ko.ips`
- 로컬 실행용 ROM: `build/stage_patch/Gun Nac (Korean).nes`
- 빌드 결과 및 체크섬: `build/build_result.json`

번역을 수정했다면 마지막 명령의 `--check-reference`를 빼세요. 이 옵션은 기존 검토판과 바이트 단위로 동일한 결과인지 확인하는 용도입니다.

## 대상 ROM

**16바이트 iNES 헤더를 포함한 파일 전체**의 값입니다. 파일 이름보다 이 해시를 기준으로 판별합니다. ZIP, 헤더를 제거한 PRG+CHR, 영어 번역판, 이미 패치한 ROM은 대상이 아닙니다.

| 항목 | 값 |
| --- | --- |
| 대상 | Gun Nac (Japan), iNES, trainer 없음 |
| 크기 | 262,160바이트 |
| CRC32 | `F39B41A4` |
| MD5 | `029daa688d2c51a296eb4e7fed953d0d` |
| SHA-1 | `48ce296d9ddb59abf13ceccde777a3e43c27ff61` |
| SHA-256 | `08ead6a2a83a7c476ac76a067a04055a6f68fe5b50248ea873d00305111da44d` |

기계 판독용 값: [config/rom.json](config/rom.json). 현재 검토판 결과는 524,304바이트, SHA-256 `da74835ad0d531ecfcc4425c135a814ddba4bfe7fd32874d9749a03a549aa6d0`입니다. [기준 빌드 기록](config/reference_build.json)

## 편집과 문서

| 목적 | 파일 |
| --- | --- |
| 본문·설정·상점·스태프롤 번역 수정 | [translation/text.csv](translation/text.csv) |
| 스테이지·그림 자막과 원본 유지 결정 | [translation/graphics.csv](translation/graphics.csv) |
| 명시적인 본문 줄바꿈 | [translation/layout_overrides.json](translation/layout_overrides.json) |
| 영어로 유지하기로 한 설정 표기 | [translation/display_overrides.json](translation/display_overrides.json) |
| 도구 설치, 빌드, 수정 방법 | [빌드 안내](docs/BUILD.ko.md) |
| 글꼴 이름·공식 출처·라이선스 | [폰트 안내](docs/FONTS.ko.md) |
| 다음 작업자를 위한 주소·구조 설명 | [구현 인수인계](docs/ARCHITECTURE.ko.md) |
| 다른 패미콤 게임에도 적용할 교훈 | [한글화 노하우](docs/NES_LOCALIZATION_NOTES.ko.md) |
| 실행 검증과 테스트 한계 | [검증 안내](docs/TESTING.ko.md) |
| GitHub 계정으로 업로드하는 절차 | [GitHub 게시 안내](docs/GITHUB.ko.md) |

## 구현 범위

오프닝·엔딩 본문, 설정, 스태프롤, 상점, 그림 자막 5개와 스테이지 이름 8개를 통합했습니다. 본문 계열은 Galmuri11-Condensed, 스테이지는 도스명조 16px, 그림 자막은 도스이야기 16px를 사용합니다. 확인된 영문·숫자·기호는 로컬 원본 ROM의 글꼴을 재사용하는 B2 정책입니다.

그래픽 작업표 30개 중 13개를 적용하고, 원본 유지로 검토된 17개를 유지했습니다. 그림 안의 일본어를 지우는 방식이 아니라 그림 위에 별도 한국어 자막을 놓는 방식입니다. 일반·하드·이판사판 엔딩 그림은 16px 내렸습니다.

MMC3/mapper 4를 유지하고 PRG와 CHR을 각각 256 KiB로 확장했습니다. 마지막 스테이지 이름 작업은 추가 확장 없이 처리했습니다. 승인된 번역 범위는 구현됐으며, 최종 화면 검토와 전 구역 플레이 테스트는 별도입니다.

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md)를 먼저 읽어 주세요. 게임/폰트 파일을 Issue·PR·Actions artifact에 첨부하지 않습니다. 코드와 연구 문서의 재사용 범위, 게임/폰트/번역의 권리 구분은 [권리 안내](docs/RIGHTS.ko.md)에 정리했습니다.

## 라이선스

자체 도구 코드와 기술 문서는 [MIT 라이선스](LICENSE)로 제공합니다. 한국어 번역문·원작 유래 자료·외부 폰트는 적용 대상에서 제외합니다. 자세한 [적용 범위](docs/RIGHTS.ko.md#라이선스-적용-범위)를 확인하세요.
