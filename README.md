# 서울경제신문 스타일북 MCP 서버

서울경제신문 스타일북을 검색하고 조회할 수 있는 MCP(Model Context Protocol) 서버입니다. 이 서버는 기자와 편집자가 기사 작성 시 스타일북 규칙을 쉽게 참조할 수 있도록 설계되었으며, LLM(대규모 언어 모델)과 연동하여 스타일북 정보를 검색하고 활용할 수 있습니다.

## 주요 기능

- **스타일북 메타데이터 조회**: 스타일북의 전체 구조와 카테고리 정보 제공
- **규칙 검색**: 키워드 기반 스타일북 규칙 검색
- **Claude 검색 연동**: Claude AI를 활용한 고급 컨텍스트 검색
- **JSON 데이터 다운로드**: 스타일북 규칙 JSON 파일 다운로드
- **스미더리 MCP 통합**: 스미더리 플랫폼과 호환되는 MCP 프로토콜 지원

## 설치 방법

### 요구사항

- Python 3.8 이상
- Flask
- aiohttp

### 기본 설치

```bash
# 저장소 복제
git clone https://github.com/yourusername/stylebook-mcp-server.git
cd stylebook-mcp-server

# 의존성 설치
pip install -r requirements.txt
```

### Docker로 실행

```bash
# Docker 이미지 빌드
docker build -t stylebook-mcp-server .

# Docker 컨테이너 실행
docker run -p 5012:5012 -v /path/to/stylebook/data:/app/data stylebook-mcp-server
```

## 사용 방법

### 서버 실행

```bash
# 기본 실행
python stylebook_mcp_server.py --data_path /path/to/stylebook/data

# 디버그 모드로 실행
python stylebook_mcp_server.py --data_path /path/to/stylebook/data --debug

# 포트 지정
python stylebook_mcp_server.py --data_path /path/to/stylebook/data --port 8000
```

### 사용 가능한 명령줄 옵션

| 옵션          | 설명                               | 기본값  |
| ------------- | ---------------------------------- | ------- |
| `--host`      | 서버 호스트                        | 0.0.0.0 |
| `--port`      | 서버 포트                          | 5012    |
| `--debug`     | 디버그 모드 활성화                 | False   |
| `--stdio`     | 표준 입출력 모드 (스미더리 연동용) | False   |
| `--verbose`   | 자세한 로깅                        | False   |
| `--data_path` | 스타일북 데이터 경로               | .       |

### API 엔드포인트

- `/.well-known/mcp/smithery.json`: MCP 검색 엔드포인트
- `/mcp`: MCP API 엔드포인트
- `/config`: 서버 설정 정보
- `/tools`: 사용 가능한 도구 목록
- `/health`: 서버 상태 확인

### MCP 도구 목록

이 서버는 다음과 같은 MCP 도구를 제공합니다:

1. **get_metadata**: 스타일북 메타데이터를 반환합니다.
2. **get_categories**: 스타일북 카테고리 목록을 반환합니다.
3. **get_rule**: 특정 규칙 ID에 해당하는 스타일북 규칙을 반환합니다.
4. **search**: 키워드로 스타일북을 검색합니다.
5. **claude_search**: Claude AI를 사용하여 스타일북을 검색합니다.
6. **download_json**: 스타일북 JSON 파일을 다운로드합니다.

## 스미더리 연동 방법

### 스미더리에 배포하기

1. 저장소를 스미더리에 연결합니다.
2. `smithery.yaml` 파일이 올바르게 구성되어 있는지 확인합니다.
3. 스미더리 대시보드에서 배포 버튼을 클릭하여 서비스를 배포합니다.

### 스미더리 MCP 클라이언트에서 사용하기

스미더리 클라이언트에서 다음과 같이 서버를 사용할 수 있습니다:

```javascript
// 메타데이터 가져오기
{
  "tool": "get_metadata",
  "parameters": {}
}

// 규칙 검색하기
{
  "tool": "search",
  "parameters": {
    "query": "외래어 표기법"
  }
}

// 특정 규칙 가져오기
{
  "tool": "get_rule",
  "parameters": {
    "rule_id": "ST-GUIDE-WRITING-001"
  }
}
```

## 데이터 구조

스타일북 데이터는 다음과 같은 구조의 JSON 파일로 구성됩니다:

```
/path/to/stylebook/data/
├── metadata.json              # 메타데이터
├── 기사작성 요령/              # 카테고리
│   ├── ST-GUIDE-WRITING-001.json
│   └── ST-GUIDE-WRITING-002.json
├── 자주 틀리는 말/             # 카테고리
│   ├── ST-GUIDE-FOREIGN-WORDS-DETAILED-001.json
│   ├── ST-GUIDE-GRAMMAR-RULES-002.json
│   └── 문법/                  # 하위 카테고리
│       ├── GRAMMAR-PARTS-OF-SPEECH-001.json
│       └── ...
└── ...
```

## 기여 방법

1. 이 저장소를 포크합니다.
2. 새 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`).
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`).
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`).
5. Pull Request를 생성합니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 문의

프로젝트에 관한 질문이나 제안이 있으시면 이슈를 등록해주세요.
