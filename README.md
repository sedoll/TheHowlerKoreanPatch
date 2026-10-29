# Howler 한글 패치

Steam판 **Howler**(The Howler)의 비공식 한국어 패치입니다.

게임 파일은 들어 있지 않습니다. 각자 가진 게임 파일에 스크립트를 실행해 자기 PC에서 한글판을 만듭니다.

## 다운로드

**[최신 릴리스 받기](https://github.com/sedoll/TheHowlerKoreanPatch/releases/latest)**

릴리스 페이지의 **Source code (zip)**을 받으면 됩니다. 설치 방법은 아래 [설치](#설치)를 참고하세요.

## 번역 범위

| 구분 | 내용 |
| --- | --- |
| 스토리·임무 | 모든 사건의 소개문과 임무 목표 |
| 메뉴·화면 | 메인 화면, 사건 번호, 음성 모드, 설정, 일시정지, 점수, 결과 화면, 엔딩 |
| 실패·성공 메시지 | "시간 초과", "사건 해결!" 등 |
| 조작 도움말 | 레벨별 도움말 오버레이 15개 (PC판 조작인 마우스와 스페이스 키 기준) |
| 이미지 속 글자 | 로딩 화면 소개문, 상점 항목, "끝" 화면, "눌러서 도움말" |
| 게임 소개 | 이야기(The Story) 화면 |

번역하지 않은 것은 **The Howler** 로고(고유명사)와 Howler.com / facebook 링크입니다.

## 필요한 것

- Steam판 Howler
- [Python](https://www.python.org/downloads/) 3.8 이상. 없으면 `install.bat`이 설치를 도와줍니다.

## 설치

1. [최신 릴리스](https://github.com/sedoll/TheHowlerKoreanPatch/releases/latest)의 **Source code (zip)**을 받아 게임 폴더 **안에** 압축을 풉니다. 폴더 이름(예: `TheHowlerKoreanPatch-1.0.0`)은 무엇이든 괜찮습니다.

   ```
   C:\Program Files (x86)\Steam\steamapps\common\Howler\
   ├─ Howler.exe
   ├─ Howler.swf
   ├─ media\
   └─ TheHowlerKoreanPatch-1.0.0\      ← 압축 푼 폴더
      ├─ install.bat
      └─ ...
   ```

   > Steam 라이브러리 → Howler 우클릭 → 관리 → 로컬 파일 보기 로 게임 폴더를 열 수 있습니다.

2. **`install.bat`을 더블클릭**합니다. 끝!

`install.bat`은 다음 일을 알아서 처리합니다.

- Python을 찾고, 없으면 winget으로 설치할지 묻습니다. 설치 뒤에는 `install.bat`을 한 번 더 실행하세요.
- 필요한 라이브러리(Pillow, numpy)가 없으면 설치합니다.
- 게임 폴더에 쓸 권한이 없으면 관리자 권한을 요청합니다. 창이 뜨면 "예"를 누르세요.
- 게임이 켜져 있으면 끌 때까지 기다립니다.
- 원본 파일을 `Howler.swf.orig`와 `orig\` 폴더에 백업한 뒤 한글판을 만듭니다.

<details>
<summary>직접 명령어로 설치하기</summary>

```bash
py -m pip install -r requirements.txt
py make_patch.py
```

</details>

## 되돌리기

**`uninstall.bat`을 더블클릭**하면 백업해 둔 원본 파일이 제자리로 돌아갑니다. Steam의 **게임 파일 무결성 확인**으로도 원본으로 돌아갑니다.

## 자주 묻는 질문

**게임 업데이트나 무결성 확인 뒤 다시 영어로 나와요.**
`install.bat`을 다시 실행하세요. 패치는 항상 백업된 원본에서 새로 만들어지기 때문에 여러 번 실행해도 됩니다.

**"패치 대상 원본(Steam판)과 다릅니다"라는 메시지가 나와요.**
이 패치는 Steam판 `Howler.swf`(SHA-256 `dfac8e9f…8b64ac3`)를 기준으로 만들었습니다. Steam에서 게임 파일 무결성 확인을 하고, 패치 폴더의 `orig\` 폴더와 `Howler.swf.orig`를 지운 뒤 다시 실행하세요.

## 번역 고치기

| 파일 | 내용 |
| --- | --- |
| `ko.json` | 게임 코드 안의 문장. `"영어 원문": "번역"` 형식 |
| `ko_help.json` | 레벨 도움말 이미지. `block`은 자동으로 찾은 글자 덩어리 번호, `en`은 참고용 원문 |

고친 뒤 `install.bat`을 다시 실행하면 반영됩니다. 번역에 새 글자를 쓰면 비트맵 폰트에도 자동으로 추가됩니다. 단, 아래 폰트에 없는 기호(「」『』 등)는 게임에 표시되지 않습니다.

## 동작 방식

Howler는 Adobe AIR + Starling 엔진 게임입니다. 글자는 비트맵 폰트로 그리고, 도움말은 128px 타일로 잘린 이미지입니다.

- `make_patch.py`: `Howler.swf`의 압축을 풀고 ActionScript 문자열 풀의 영어 문장을 교체합니다. Phaeton 비트맵 폰트 4종에는 한글 글리프를 추가합니다.
- `images.py`: 메뉴 아틀라스, 로딩 화면, 사건 번호 배경에 그려진 글자를 지우고 한글로 다시 그립니다.
- `helpoverlay.py`: 레벨 도움말 타일을 원래 배치로 합칩니다. 글자 덩어리만 찾아 지우고(화살표와 점선은 남김) 한글을 그린 뒤, 다시 타일로 잘라 아틀라스와 좌표 XML을 고칩니다.
- `swf.py`, `abcfile.py`: SWF 태그와 ABC(ActionScript 바이트코드) 상수 풀을 읽고 씁니다.

## 글꼴

한글 글자에는 Pear Type Foundry의 **[우아한세리프 (GraceSerif)](https://noonnu.cc/font_page/1800) Bold**를 사용했습니다. 이 글꼴은 [SIL Open Font License 1.1](fonts/GraceSerif-LICENSE.txt)로 배포됩니다.

한글 글자는 그림(비트맵)으로 바꿔서 게임에 넣으며, 폰트 파일 자체는 게임에 들어가지 않습니다.

## 주의

- 이 패치는 원작자(Antanas Marcelionis, Rene Petruliene)와 관계없는 **비공식 팬 번역**입니다.
- 게임 원본 파일(`Howler.swf`, `media` 이미지, 그리고 그 백업인 `Howler.swf.orig`, `orig\`)은 저작권 문제로 이 저장소에 포함하지 않습니다. `.gitignore`에도 제외되어 있습니다.
