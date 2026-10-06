# 검증 절차와 범위

## 외부 에셋이 없는 검사

```sh
python3 tools/check_sources.py
python3 tools/audit_public.py
```

GitHub Actions도 이 범위만 실행합니다. ROM·폰트를 GitHub Secrets나 Actions artifact로 전달하지 않습니다. CI 통과는 패치의 실제 실행 검증이나 법률 검토를 뜻하지 않습니다.

## 재현 빌드

사용자가 권한 있는 ROM·번역 자료와 정확한 BDF를 준비한 로컬 환경에서 실행합니다.

```sh
python3 tools/build.py --rom "/path/to/Gun Nac (Japan).nes" --check-reference
```

기준 번역으로 생성된 결과는 ROM SHA-256 `da74835ad0d531ecfcc4425c135a814ddba4bfe7fd32874d9749a03a549aa6d0`, IPS SHA-256 `737c6cae6960704b06430a5c7f81420106775d0370c1ce9806414a205ea7f84b`입니다. 번역을 바꾼 경우 이 값과 같을 필요가 없으며 `--check-reference`를 뺍니다. 빌더는 매 단계에서 원본에 IPS를 재적용해 생성 ROM과 동일한지 검사합니다.

공개용 소스에서 원문·로고 토큰·역사적 중간 파일을 제거한 뒤 새 폴더에서 공식 폰트를 받아 빌드했고, 두 해시가 기준판과 일치했습니다. 이는 재현 가능성 검사이며 공개 이용허락 여부의 검증은 아닙니다.

## Mesen 실행 검사

Mesen libretro core가 필요합니다. 일반 Mesen 앱 실행 파일이 아니라 Python과 같은 CPU 아키텍처의 `.dylib` / `.so` / `.dll`입니다. 검증된 조합은 macOS/Python 3.14.7/Mesen libretro 0.9.9입니다. 다른 버전과 플랫폼에서는 별도 확인이 필요합니다.

```sh
export MESEN_CORE="/path/to/mesen_libretro.dylib"
python3 tools/verify_story_runtime.py opening --rom "build/stage_patch/Gun Nac (Korean).nes" --out build/runtime/final_opening
python3 tools/verify_story_runtime.py ending --rom "build/stage_patch/Gun Nac (Korean).nes" --out build/runtime/final_ending
python3 tools/verify_settings_runtime.py ko --rom "build/stage_patch/Gun Nac (Korean).nes" --out build/runtime/final_settings
python3 tools/verify_credits_runtime.py --rom "build/stage_patch/Gun Nac (Korean).nes" --out build/runtime/final_credits
python3 tools/verify_stage_runtime.py
python3 tools/verify_stage_clear.py
```

macOS의 일반 RetroArch 코어 경로가 있으면 환경변수를 생략할 수 있습니다. 하드코딩된 개인 사용자 경로는 없습니다. Windows PowerShell에서는 `$env:MESEN_CORE`에 DLL 경로를 설정합니다.

상점은 다음 시나리오가 있습니다. 수정한 경우 관련 시나리오와 일본어 원본의 상태 결과를 함께 비교합니다.

```sh
python3 tools/verify_shop_runtime.py ko purchase --rom "build/stage_patch/Gun Nac (Korean).nes" --out build/runtime/final_shop_purchase
python3 tools/verify_shop_runtime.py jp purchase --out build/runtime/jp_shop_purchase
```

`welcome`, `purchase`, `shipping`, `delivery`, `blocked`, `converter`를 지원합니다. 배송은 `--bomb-type 0..3`, `--quantity`로 분기합니다. 기록 JSON의 `checks`는 게임 상태, `verified_records`는 픽셀 검사입니다. 문자열을 변경하면 이전 승인 마스크가 아니라 새 빌드의 예상 마스크를 기준으로 다시 실행해야 합니다.

`verify_caption_cards.py`는 그림 카드 직접 호출 fixture로 전후 그림을 비교합니다. 프로젝트 루트에서 실행하세요. 본문·스태프롤 검사의 엔딩 직행 사본, 구역 선택 RAM, CLEAR 상태는 검증에만 사용하며 배포 ROM에는 들어가지 않습니다.

## 기존 기준판의 결과

- 오프닝 11개·엔딩 8개 본문 화면.
- 설정 106개 상태 체크포인트, 원본과 의미상 상태 일치.
- 스태프롤 43개 텍스트 레코드, 모든 세로 8픽셀 위상.
- 스테이지 8개, 각각 229개 연속 프레임의 글자·그림자 검증, 이름 종료 후 진행.
- AREA/CLEAR 구역 1·7·8 비교.
- 그림 자막 5개 및 그림 이동·마지막 회사 로고 위치 확인.
- 상점 기존 통합 단계 126개 상태 체크, 22개 출력 레코드.

전체 정상 플레이 8구역 클리어·모든 숨은 분기·실기·다른 에뮬레이터는 미검증입니다. 글자 처리 시간이 달라져 이후 난수·적 배치까지 모든 프레임이 원본과 같다는 의미도 아닙니다. 재현한 최종 ROM이 같은 해시라면 기존 검증 대상과 같은 바이트지만, 새 도구 환경의 실행 테스트를 대신하지는 않습니다.
