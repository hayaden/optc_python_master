# optc-python
이 프로젝트는 (https://github.com/daye10/optc-python)을 기반으로 포크한 버전입니다.
원본 프로젝트의 구조와 로직을 유지하되, 한글 버전 DB(sakura_ko.db)에 맞게 수정 작업 진행

## Requirements

* Python 3
* pip

## Installation

```
git clone https://github.com/hayaden/optc_python_master
cd optc_python_master
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Usage

### 인게임 DB 다운로드
 * download_SakuraDB.py 실행하면
 * data 폴더에 sakura_ko.db 파일 생성 --> SQLite format으로 인겜 정보가 대부분 포함
 * SQLite format을 읽을 수 있는 PC/핸드폰 앱으로 조회도 가능

### 캐릭터 정보 및 아이콘 다운로드
* sakura_ko.db의 MstCharacter_ 테이블에서 원하는 캐릭터의 severId_ 확인 
* `main.py`실행, id_range = (14500, 14590)으로 캐릭터 이미지 다운받고자 하는 server_id  범위를 지정
* 실행하면 다음 파일 생성
  - sakura_ko.db: 인게임 한글 DB 데이터
  - *.png: 각 캐릭의 일러스트 및 아이콘(썸네일)
  - details_kor.js: DB용 캐릭터 세부 정보 (선장효과, 필살기, 적제 능력, 태그 등등)
  - characterTags.js: DB용 캐릭터 태그 정보 
  - units.js DB: 테이블 구성용 캐릭터 정보

### 최신 트맵 패턴 정보
* TM_Gimmick_generate_index.py 실행
* 실행하면 docs폴더에 index.html 생성


### 최신 유대 패턴 정보
* 추가 예정

### Bisque

Contains methods to encrypt and decrypt game's requests, see `bisqueDoc.py` for more details.