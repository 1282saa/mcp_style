# 서울경제신문 스타일북 MCP 서버

이 프로젝트는 서울경제신문 스타일북 데이터를 MCP(Model Context Protocol) 서버로 제공하는 도구입니다.

## 설치 방법

### 필수 라이브러리 설치

```bash
pip install -r requirements.txt
```

## 기본 사용법

### 1. 직접 실행

```bash
python stylebook_mcp_fastmcp.py --stdio --data_path "기사 작성 준칙"
```

### 2. 스미더리 연동

1. 스미더리를 설치합니다.
2. `smithery.yaml` 파일을 스미더리 디렉토리에 복사합니다.
3. 스미더리에서 `@your-username/mcp_style`을 배포합니다.

### 3. 클로드 데스크탑 연동

1. `claude_desktop_config.json` 파일을 홈 디렉토리의 적절한 위치에 복사합니다:

   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. 클로드 데스크탑을 재시작합니다.

## 테스트 방법

```bash
# 기본 테스트
python test_mcp.py

# 특정 데이터 경로와 함께 테스트
python test_mcp.py --data-path "기사 작성 준칙"

# 특정 검색어로 테스트
python test_mcp.py --query "문장부호"
```

## MCP Inspector로 테스트

```bash
npx @modelcontextprotocol/inspector python -u stylebook_mcp_fastmcp.py --stdio --data_path "."
```

## 디렉토리 구조

이 MCP 서버는 다음과 같은 파일 구조를 사용합니다:

```
.
├── smithery.yaml                # 스미더리 설정 파일
├── stylebook_mcp_fastmcp.py     # MCP 서버 메인 스크립트
├── claude_desktop_config.json   # 클로드 데스크탑 설정 파일
├── test_mcp.py                  # 테스트 스크립트
├── requirements.txt             # 필수 라이브러리 목록
└── README.md                    # 이 문서
```

## 스타일북 데이터 구조

스타일북 데이터는 다음과 같은 디렉토리에 있어야 합니다 (기본적으로 스크립트는 자동으로 검색합니다):

```
.
├── 기사 작성 준칙/
├── 기사작성 요령/
├── 자주 틀리는 말/
├── 제목과 레이아웃_제목달기/
├── 제목과 레이아웃_레이아웃 요령/
└── 뉴스가치 판단/
```

각 디렉토리에는 `.json` 파일들이 있어야 하며, 메타데이터는 `metadata.json` 또는 `_meta.json` 파일에 있어야 합니다.

## 도구 목록

MCP 서버는 다음과 같은 도구를 제공합니다:

1. `get_metadata` - 스타일북 메타데이터 조회
2. `get_categories` - 스타일북 카테고리 목록 조회
3. `get_rule` - 특정 규칙 ID로 스타일북 규칙 조회
4. `search` - 키워드로 스타일북 검색
5. `claude_search` - Claude AI를 사용한 스타일북 검색
6. `download_json` - 스타일북 JSON 파일 다운로드

## 환경 변수

- `PYTHONUNBUFFERED`: 항상 1로 설정하여 버퍼링을 비활성화
- `PYTHONIOENCODING`: `utf-8`로 설정하여 한글 등 유니코드 문자를 올바르게 처리

## 문제 해결

1. 데이터를 찾을 수 없는 경우:

   - `--data_path` 옵션으로 정확한 경로를 지정하세요.
   - 스크립트가 자동으로 여러 디렉토리를 검색하지만, 직접 지정하는 것이 더 확실합니다.

2. 클로드 데스크탑에 연결되지 않는 경우:

   - 로그를 확인하세요: `tail -n 20 -F ~/Library/Logs/Claude/mcp*.log`
   - `claude_desktop_config.json` 파일이 올바른 위치에 있는지 확인하세요.

3. 스미더리에 연결되지 않는 경우:
   - 스미더리 로그를 확인하세요.
   - `smithery.yaml` 파일이 올바르게 설정되었는지 확인하세요.

## 라이선스

이 프로젝트는 자유롭게 사용할 수 있습니다.

@mcp.route("resources/list")
def handle_resources_list():
return {"resources": []}

@mcp.route("prompts/list")
def handle_prompts_list():
return {"prompts": []}

@mcp.route("debug/status")
def debug_status():
return {
"loaded_data": len(stylebook_data),
"server_uptime": "...",
"memory_usage": "..."
}
