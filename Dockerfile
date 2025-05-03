FROM python:3.10-slim

WORKDIR /app

# 필요한 시스템 패키지 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 필요한 Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV DEBUG_MCP=1
ENV MCP_TIMEOUT=180
ENV LANG=ko_KR.UTF-8

# 한국어 로케일 설정
RUN apt-get update && \
    apt-get install -y locales && \
    localedef -i ko_KR -c -f UTF-8 -A /usr/share/locale/locale.alias ko_KR.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

# 기본 데이터 경로 설정
ENV DATA_PATH=.

# 컨테이너 실행 시 기본 명령 (Smithery가 덮어쓰지만 기본값으로 필요)
CMD ["python", "-u", "stylebook_mcp_fastmcp.py", "--stdio", "--verbose", "--data_path", "."] 