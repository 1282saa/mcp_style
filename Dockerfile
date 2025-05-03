FROM python:3.10-slim

WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 표준 출력 버퍼링 비활성화 (실시간 로그용)
ENV PYTHONUNBUFFERED=1

# 컨테이너 실행 시 기본 명령 (Smithery가 덮어쓰지만 기본값으로 필요)
CMD ["python", "stylebook_mcp_server.py", "--stdio"] 