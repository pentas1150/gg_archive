# GG Archive

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-41CD52?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

스타크래프트 리마스터 전적 기록 및 상대 분석 프로그램

<br>

## 소개

**GG Archive**는 스타크래프트 리마스터에서 게임이 끝날 때마다 `LastReplay.rep` 파일의 변화를 감지하여 자동으로 전적을 기록해주는 데스크톱 애플리케이션입니다.

래더 게임을 하다 보면 같은 상대를 여러 번 만나게 되는데, "이 사람 어떻게 플레이했더라?", "저번에 뭘로 이겼지?" 같은 생각이 들 때가 많습니다. 하지만 이런 정보를 기록할 마땅한 곳이 없어서 만들게 되었습니다.

**배포는 Windows만 진행하고 있습니다.**

<br>

## 주요 기능

### 자동 리플레이 감지
- `LastReplay.rep` 파일 변화를 실시간으로 감지
- 게임 종료 시 자동으로 전적 기록
- 백그라운드에서 조용히 동작 (시스템 트레이)

### 상대별 전적 관리
- 상대 플레이어별 승/패/승률 통계
- 맵별 전적 분석
- APM, EAPM 기록

### 상대 메모 기능
- 상대방의 플레이 스타일 메모
- 자주 쓰는 빌드, 특징 등 자유롭게 기록
- 다음에 만났을 때 참고 가능

### 기타 기능
- SQLite 기반 로컬 데이터 저장
- 데이터베이스 백업 기능
- AutoSave 리플레이 일괄 불러오기

<br>

## 설치

### 요구 사항
- Python 3.11
- 스타크래프트 리마스터
- **screp v1.12.16 (최상위에 위치 필수!!)**
    - https://github.com/icza/screp/releases/download/v1.12.16/screp-v1.12.16-windows-amd64.zip

### 설치 방법 (소스 기반)
```bash
# 저장소 클론
git clone https://github.com/your-username/gg_archive.git
cd gg_archive

# Poetry로 의존성 설치 (poetry 가상 환경 X)
poetry config virtualenvs.create false
poetry install --no-root

# 실행
python main.py
```

### 설치 방법 (.exe 기반)
- Release에서 최신 버전의 GG_Archive.zip을 다운로드 한 후, 압축해제

<br>

## 사용법

### 초기 설정
1. 프로그램 실행 후 설정 화면에서 스타크래프트 경로 지정
2. 본인의 게임 ID 입력
3. 설정 저장 후 자동으로 리플레이 감시 시작

### 기본 사용
1. 프로그램을 실행한 상태로 스타크래프트 게임 진행
2. 게임 종료 시 자동으로 전적 기록
3. 상대 더블 클릭하여 상세 전적 및 메모 확인/수정

### 시스템 트레이
- 창을 닫아도 백그라운드에서 계속 동작
- 트레이 아이콘 더블클릭으로 창 다시 열기
- 우클릭 메뉴에서 종료 가능

<br>

## 기술 스택

- **GUI**: PySide6 (Qt for Python)
- **데이터베이스**: SQLAlchemy + SQLite
- **파일 감시**: watchdog
- **데이터 검증**: Pydantic

<br>

## 빌드

### Windows
```bash
./build.bat
```

### macOS / Linux
```bash
./build.sh
```

<br>

## 라이선스

MIT License

<br>

## 기여

버그 리포트나 기능 제안은 Issues에 등록해 주세요.

<br>

## Acknowledgements

- [screp](https://github.com/icza/screp) - 스타크래프트 리플레이 파서. 이 프로젝트 덕분에 리플레이 분석이 가능했습니다.
