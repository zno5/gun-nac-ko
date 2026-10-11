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

기준 번역으로 생성된 결과는 ROM SHA-256 `2172180d38969212372aff8400191c26ac378bc6abc7432fe0ba9edbf0610813`, IPS SHA-256 `749f0d0a603bdbf773d28b2f900957f91a184054fd60f3cb7a08452656689db4`입니다. 번역을 바꾼 경우 이 값과 같을 필요가 없으며 `--check-reference`를 뺍니다. 빌더는 매 단계에서 원본에 IPS를 재적용해 생성 ROM과 동일한지 검사합니다.

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
- 스테이지 9개(AREA-0 포함), 각각 229개 연속 프레임의 글자·그림자 검증, 이름 종료 후 진행.
- AREA/CLEAR 구역 1·7·8 비교.
- 그림 자막 5개 및 그림 이동·마지막 회사 로고 위치 확인.
- 상점 기존 통합 단계 126개 상태 체크, 22개 출력 레코드.

전체 정상 플레이 8구역 클리어·모든 숨은 분기·실기·다른 에뮬레이터는 미검증입니다. 글자 처리 시간이 달라져 이후 난수·적 배치까지 모든 프레임이 원본과 같다는 의미도 아닙니다. 재현한 최종 ROM이 같은 해시라면 기존 검증 대상과 같은 바이트지만, 새 도구 환경의 실행 테스트를 대신하지는 않습니다.

## AREA-0 수정 검증 (2026-10-11)

숨겨진 구역 제목을 ‘별의 별’로 추가했습니다. AREA-0의 원본 코드가 교체된 CHR을 참조하던 오류를 수정했습니다. 0~8 구역 각각 229프레임 제목/그림자 검사와 표시 종료 후 진행을 확인했고 AREA/CLEAR는 0·1·7·8에서 기존 표시와 비교했습니다. 시작 구역은 RAM으로 지정했으며 정상 플레이의 숨겨진 구역 진입 조건은 검증하지 않았습니다.

RC1과의 차이는 제목 코드/데이터 105바이트뿐이며 기존 1~8 제목 배치와 전체 CHR 및 다른 번역 데이터는 동일합니다. 공개 소스 전체 빌드와 로컬 빌드의 ROM/IPS 해시가 일치했습니다.

윙과 제목이 겹칠 때 스프라이트 표시 한도로 기체가 잘리는 문제는 아직 남아 있습니다. 4·7·8 압축 글꼴 시안은 이 수정에 적용하지 않았습니다.

## 엔딩 → 스태프롤 전환 수정 (2026-10-11)

스태프롤 포인터 초기화 직후 화면에 남은 마지막 엔딩 대사가 다른 글꼴로 읽히던 문제를 수정했습니다. 포인터 $8000..$8003의 초기 빈 이벤트 동안 엔딩 글꼴을 유지하고 첫 텍스트 이벤트에서 스태프롤 글꼴로 전환합니다. 최초 3개 이벤트가 빈 이벤트라는 전제는 빌드 시 검사합니다.

`python3 tools/verify_credits_transition.py`는 엔딩 글꼴을 강제한 테스트 대조 ROM과 전환 전후 화면을 프레임별로 비교하고 이후 글꼴 전환도 확인합니다. 기존 스태프롤 전체 글자/8개 스크롤 위상 검사도 다시 통과했습니다. 테스트는 엔딩 직행용 ROM 복사본에서 수행하며 배포 ROM에는 직행 코드를 넣지 않습니다.
