# Smithery 배포 가이드

스타일북 MCP 서버를 Smithery에 배포하는 방법에 대한 가이드입니다.

## 준비 사항

1. Smithery 계정 및 CLI 설치
2. Docker 설치 (배포용 이미지 빌드에 필요)
3. 필요한 파일:
   - `stylebook_mcp_fastmcp.py` (MCP 서버 스크립트)
   - `Dockerfile` (배포 이미지 빌드용)
   - `requirements.txt` (필요한 패키지 목록)
   - `smithery.yaml` (Smithery 배포 설정)

## 로컬 테스트

배포 전에 로컬에서 Docker 이미지가 제대로 빌드되는지 확인하세요:

```bash
# Docker 이미지 빌드
docker build -t stylebook-mcp .

# 이미지 테스트 실행
docker run -it --rm stylebook-mcp
```

## Smithery 배포 절차

1. Smithery에 로그인:

   ```bash
   smithery login
   ```

2. 배포 전 확인:

   ```bash
   smithery verify
   ```

3. MCP 서버 배포:

   ```bash
   smithery deploy
   ```

4. 배포 상태 확인:
   ```bash
   smithery list
   ```

## 환경 변수 설정

Smithery 배포는 다음 환경 변수를 사용합니다:

- `PYTHONUNBUFFERED=1`: Python 출력 버퍼링 비활성화
- `PYTHONIOENCODING=utf-8`: 한글 출력을 위한 인코딩 설정
- `DEBUG_MCP=1`: MCP 디버깅 활성화
- `MCP_TIMEOUT=180`: MCP 요청 타임아웃 설정
- `LANG=ko_KR.UTF-8`: 한국어 로케일 설정

## 배포 후 확인

배포가 완료되면 다음 명령으로 MCP 서버를 Claude에 설치할 수 있습니다:

```bash
smithery install @사용자ID/mcp_style
```

설치 후 Claude나 Cursor에서 MCP 도구가 표시되는지 확인하세요.

## 문제 해결

- **Docker 빌드 오류**: 로컬에서 Docker 이미지가 정상적으로 빌드되는지 확인
- **배포 실패**: `smithery logs` 명령으로 배포 로그 확인
- **타임아웃 오류**: `smithery.yaml`의 타임아웃 설정 및 환경 변수 확인
- **도구 목록 표시 안됨**: MCP 메서드 구현 및 초기화 코드 확인
