FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5012

# 기본 실행 명령
CMD ["python", "stylebook_mcp_server.py", "--host", "0.0.0.0", "--port", "5012", "--data_path", "."] 