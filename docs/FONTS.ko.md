# 사용 글꼴과 공식 출처

폰트 파일과 래스터화한 글자 이미지는 저장소에 넣지 않습니다. 필요한 파일을 공식 배포처에서 별도로 받습니다. 이름만 같아도 다른 버전이면 결과가 달라질 수 있으므로 고정 커밋과 SHA-256을 함께 사용합니다.

| 사용처 | 글꼴 | 공식 배포처 | 배포 안내 |
| --- | --- | --- | --- |
| 본문·설정·상점·스태프롤의 한글 | Galmuri11-Condensed | [quiple/galmuri](https://github.com/quiple/galmuri) | [SIL OFL 1.1](https://github.com/quiple/galmuri/blob/71e1cacf1437a11220307120e63e30bc275312d4/ofl.md) |
| 스테이지 이름 | DOSMyungjo, 도스명조 16px BDF | [hurss/fonts](https://github.com/hurss/fonts) | [MIT 기반 라이선스 및 예약 이름 고지](https://github.com/hurss/fonts/blob/3fc1181c6b4af095206068188c3ea966d6738add/LICENSE.txt) |
| 그림 위 자막 | DOSIyagiBoldface, 도스이야기/이야기 굵은체 16px BDF | [hurss/fonts](https://github.com/hurss/fonts) | 위와 동일. [제작자 README](https://github.com/hurss/fonts/blob/3fc1181c6b4af095206068188c3ea966d6738add/README.md) 함께 확인 |

Galmuri 제작자는 Lee Minseo(quiple), 도스 글꼴 제작자는 이담허(Damheo Lee)입니다. 도스 글꼴의 라이선스는 일반 MIT 허가문 외에 예약 글꼴 이름 안내를 포함하므로 배포문을 임의로 줄이지 않습니다. 이 문서는 라이선스 자체를 새로 부여하지 않습니다.

## 고정 입력

- Galmuri 커밋: `71e1cacf1437a11220307120e63e30bc275312d4`, `dist/Galmuri11-Condensed.bdf`, 패키지 2.40.3.
- 도스 글꼴 커밋: `3fc1181c6b4af095206068188c3ea966d6738add`, `bdf/DOSMyungjo-16.bdf`, `bdf/DOSIyagiBoldface-16.bdf`.

| 파일 | SHA-256 |
| --- | --- |
| Galmuri11-Condensed.bdf | `5adbdedb3d118e99cc7e114b746b3cf6f6a46a4642e0ff215d6a431e55901995` |
| DOSMyungjo-16.bdf | `392a67846659b06557076daf6e28f838c603a7d87a504953dbeb4113b378e39c` |
| DOSIyagiBoldface-16.bdf | `f748fc59cc25ef0f327b741789e0e28f150c07c9445e7f16491a1448ff3bb204` |

실제 다운로드 URL과 로컬 저장 위치: [config/font_sources.json](../config/font_sources.json).

## 렌더링 정책

Galmuri의 한글은 원래 BDF의 획을 유지하고 8×16 셀·baseline 14로 배치합니다. B2 정책의 영문·숫자·확인된 기호는 사용자가 준비한 일본어 ROM의 원래 글꼴을 y=5–12에 배치합니다. 굵기가 다른 문자를 일괄로 인공 볼드 처리하지 않습니다. 어떤 문자를 원본에서 가져오는지는 `tools/font_policy.py`에 명시했습니다.

도스 두 글꼴은 16px 원래 비트맵을 직접 읽습니다. 그림자 자리를 확보하기 위해 전체 획을 왼쪽으로 1px 옮긴 뒤 오른쪽 아래 1px 그림자를 추가합니다. 획을 축소하거나 잘라내지 않는지 빌드가 검사합니다. 공백과 자막의 ASCII는 반각입니다.

BDF 헤더의 인코딩 이름만 신뢰하지 않았습니다. 도스이야기는 헤더 표기와 달리 실제 사용 글자의 ENCODING을 유니코드 값으로 확인했습니다. BITMAP 줄 뒤의 공백도 허용합니다.

생성한 CHR·IPS 등에 글꼴 데이터가 포함될 수 있습니다. 이를 별도로 배포한다면 해당 폰트의 실제 허가문·출처·예약 이름 조건을 검토하고 유지해야 합니다. 이번 저장소는 그런 생성물을 배포하지 않습니다.
