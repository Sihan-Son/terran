# Terran: Territory Conquest

pygame 기반의 영토 점령 시뮬레이션 게임입니다. 여러 AI 세력이 50x50 격자 맵에서 영토를 확장하고 서로를 점령하며 최후의 승자를 가립니다.

> 자동 생성된 README 초안입니다. 코드(`main.py`)와 규칙 문서(`rule.md`)에서 관찰된 내용을 기준으로 작성되었습니다.

## 개요

- 최대 2500턴 동안 5개 세력이 자동으로 영토를 확장합니다.
- 각 세력은 AI 로직으로 점령, 전투, 수도 방어 등을 수행합니다.
- 플레이어 조작 없이 시뮬레이션이 진행되며, 화면에 격자 맵과 세력별 정보 패널이 표시됩니다.
- 게임 진행 로그가 `logs/` 폴더에 텍스트 파일로 기록됩니다.

자세한 게임 규칙(지형, 점령/전투, 세력 흡수, AI 행동 로직 등)은 [`rule.md`](rule.md)를 참고하세요.

## 주요 설정값

`main.py` 상단 상수에서 확인되는 기본 설정입니다.

- 격자 크기(`GRID_SIZE`): 50
- 세력 수(`NUM_FACTIONS`): 5
- 최대 턴(`MAX_TURNS`): 2500
- 지형 종류: 평지(plains), 농지(farmland), 산(mountain), 호수(lake)
- FPS: 15

## 기술 스택

- Python (>= 3.9)
- [pygame](https://www.pygame.org/) (>= 2.6.1)
- 패키지/환경 관리: [uv](https://github.com/astral-sh/uv) (`pyproject.toml`, `uv.lock`)

## 설치

uv 사용 시:

```bash
uv sync
```

또는 pip 사용 시:

```bash
pip install "pygame>=2.6.1"
```

## 실행

```bash
uv run main.py
```

또는:

```bash
python main.py
```

실행하면 pygame 창이 열리고 시뮬레이션이 자동으로 시작됩니다. 창을 닫으면 종료되며, 종료 시 로그 파일이 정리됩니다.

## 디렉터리 구조

```
.
├── main.py               # 게임 진입점 및 전체 로직 (Game 클래스)
├── rule.md               # 게임 규칙 문서
├── rule_update_note.md   # 규칙 업데이트 노트
├── pyproject.toml        # 프로젝트 메타데이터 및 의존성
├── uv.lock               # uv 잠금 파일
├── GEMINI.md             # Gemini 작업 컨텍스트 설정 파일
└── logs/                 # 게임 진행 로그(game_log_*.txt)
```

## 라이선스

리포지토리에 별도 라이선스 파일이 없습니다. (TODO)
