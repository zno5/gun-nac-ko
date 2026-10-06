# 빌드와 번역 수정

## 필요한 도구

| 도구 | 필수 여부 | 용도 |
| --- | --- | --- |
| Python 3.10+ | 필수 | 표준 라이브러리만으로 BDF 파싱·6502 코드 생성·ROM/IPS 생성 |
| Git | 협업 시 필수 | clone·변경 기록·공개 파일 검사 |
| 사용자 소유의 대상 일본어 ROM | 빌드 필수 | [해시](../config/rom.json)로 입력 검증 |
| 공식 BDF 3종 | 빌드 필수 | [폰트 출처](FONTS.ko.md), 저장소에 미포함 |
| Mesen libretro core | 실행 검증 시 필요 | Python의 ctypes로 로드, 기존 검증은 0.9.9 |
| unidasm / rom-tools | 선택 | 6502 역어셈블·추가 조사; 패치 생성에는 불필요 |
| GitHub CLI `gh` | 선택 | 계정 로그인·원격 저장소 생성·push |
| 이미지 편집기·ImageMagick·FreeType | 불필요 | 최종 선택 BDF는 원래 비트맵을 직접 읽음 |

Python 3.14.7/macOS에서 실제 빌드를 검증했습니다. 빌드 코드는 운영체제 독립적인 표준 라이브러리만 사용하지만, Windows/Linux의 실제 실행 결과까지 보장한 것은 아닙니다. Windows에서는 `python3` 대신 설치된 `py -3` 또는 `python` 명령을 사용합니다. `python -O`로 실행하지 마세요. 원본 바이트·용량 검사가 생략됩니다.

## 처음 받았을 때

1. 저장소를 clone하고 그 폴더에서 아래 명령을 실행합니다.
2. 자신의 원본 ROM을 저장소 바깥에 준비합니다. 영어판은 필요 없습니다.
3. 공식 폰트를 가져오고 전체를 빌드합니다.

```sh
python3 tools/check_sources.py
python3 tools/fetch_fonts.py
python3 tools/build.py --rom "/path/to/Gun Nac (Japan).nes" --check-reference
```

`fetch_fonts.py`는 HTTPS로 공식 고정 커밋의 폰트와 라이선스 안내문을 받아 `assets/`에 저장합니다. 폰트 해시가 다르면 실패합니다. 이 폴더는 공개 대상이 아닙니다. 네트워크가 차단된 경우 [font_sources.json](../config/font_sources.json)의 공식 URL에서 직접 받은 파일을 `destination` 경로에 놓아도 됩니다.

`build.py`는 ROM의 네 가지 해시를 모두 확인한 뒤 `jp/Gun Nac (Japan).nes`에 로컬 사본을 만듭니다. `jp/`에는 한 개의 `.nes`만 허용합니다. 기존에 다른 ROM이 있으면 덮어쓰지 않고 중단합니다. 원문 대사와 구조는 로컬 `analysis/jp_text.json`으로 추출하며, 공개 번역표를 덮어쓰지 않습니다.

빌드는 아래 순서입니다.

1. `build_font_preview.py`: 승인 번역과 B2 글꼴 정책으로 문자 마스크·미리보기 생성.
2. `build_story_patch.py`: PRG/CHR 확장, 본문 렌더러·글꼴 IRQ 연결.
3. `build_settings_patch.py`: 두 타일 높이 설정 행·커서 정렬.
4. `build_credits_patch.py`: 두 행 단위 스태프롤 이벤트, 원본 로고 유지.
5. `build_shop_patch.py`: 상점 번역·동적 숫자·선택 커서·지우기 영역.
6. `build_caption_patch.py`: 도스이야기 자막, 세 엔딩 카드 16px 이동.
7. `build_stage_patch.py`: 도스명조 이름·그림자·인트로 표시 우선순위.

모든 중간 결과를 재생성합니다. 이전 작업자의 `build/`, 캡처, 추출 데이터, 글꼴 비교 실험 폴더는 필요 없습니다. 단계별 로그는 `build/build_*.log`, 최종 결과는 `build/stage_patch/`입니다. IPS는 일본어 원본에 적용하는 통합 패치입니다.

## 번역만 수정할 때

`translation/text.csv`의 `ko_translation`을 수정합니다. `jp_text_offset`은 원본 파일의 주소이며 줄의 식별자입니다. 행을 임의 삭제하거나 주소·group·review_status를 바꾸지 마세요. 공개 CSV에는 일본어 원문과 원본 바이트가 없고, 필요한 원문은 로컬 추출 JSON에서 같은 주소로 찾아봅니다.

본문의 명시적 줄바꿈은 `translation/layout_overrides.json`에서 함께 바꿉니다. 번역과 줄바꿈 파일의 공백을 제외한 내용이 다르면 빌드가 실패합니다. 이 검사는 사용자의 최신 번역이 오래된 레이아웃에 의해 조용히 되돌아가는 것을 막습니다.

설정 중 영어로 유지하는 항목은 `translation/display_overrides.json`의 `reviewed_ko_text`와 최종 `text`가 분리돼 있습니다. 한국어 표만 수정해도 이 부분을 확인해야 합니다.

```sh
python3 tools/check_sources.py
python3 tools/build.py
```

`--check-reference`는 번역 수정 뒤에는 사용하지 않습니다. 결과 ROM/IPS 해시는 달라지는 것이 정상입니다. 빌드가 성공했다는 것과 실제 화면에서 잘 읽힌다는 것은 별개이므로 해당 실행 검증과 화면 검토를 진행하세요.

## 화면 배치도 수정할 때

| 영역 | 수정 위치 | 주의점 |
| --- | --- | --- |
| 본문 | `layout_overrides.json`, `build_story_patch.py` | 28셀, 8×16, 기본 최대 5줄; 특수 시작 행 존재 |
| 설정 | `build_settings_patch.py`의 `specs`·`stream` | 이전 긴 항목을 지우는 전체 행 폭 유지 |
| 상점 | `build_shop_patch.py`의 `layout`·`fields` | 가변 숫자 자리수, 단위 정렬, 배송 표시 지우기 |
| 스태프롤 | `text.csv`, `build_credits_patch.py` | 문자열 길이가 원래 x좌표 기준으로 화면을 넘지 않아야 함 |
| 그림 자막 | `graphics.csv`, `build_caption_patch.py` | 256px 한 줄, 그림 영역과 팔레트 공유 |
| 스테이지 | `graphics.csv`, `build_stage_patch.py` | 한 줄 한글 4자이면 8스프라이트 한도; `/` 대신 `／`가 줄 구분자 |

도구의 용량·원본 바이트 검사를 삭제해 오류를 넘기지 마세요. 글자 증가로 타일 한도를 넘으면 글리프 조각 공유, 화면별 폰트 분리, 문구 길이, 새 CHR 배치 순서로 설계를 다시 검토합니다. 상점에는 고정 문구 일부를 조합하는 코드가 있어 내용 변경 시 `layout` 검사가 실패할 수 있습니다. 동적 토큰 `{소지금}`, `{폭탄수량}` 등을 일반 글자로 치환하지 마세요.

## 소스만 검사·내보내기

```sh
python3 tools/audit_public.py
python3 tools/export_source.py
```

`dist/gun-nac-ko-source.zip`은 `publish_manifest.json`에 등록된 텍스트 소스만 포함합니다. ROM·폰트·PNG·IPS·분석 덤프·`.git`을 포함하지 않습니다. 작업 폴더 전체를 압축해 공유하지 마세요.
