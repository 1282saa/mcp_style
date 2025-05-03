#!/usr/bin/env python
"""
MCP 클라이언트 테스트 스크립트
"""
import json
import subprocess
import sys
import time
import os
import argparse

def send_request(process, request):
    """MCP 서버에 요청을 보내고 응답을 받습니다."""
    print(f"\n>>> 요청: {request}")
    
    # JSON 문자열로 변환 후 개행 추가
    request_str = json.dumps(request) + "\n"
    
    # 요청 전송
    process.stdin.write(request_str)
    process.stdin.flush()
    
    # 응답 대기
    time.sleep(0.5)
    
    # 응답 읽기
    response = process.stdout.readline().strip()
    if response:
        try:
            parsed = json.loads(response)
            print(f"<<< 응답: {json.dumps(parsed, ensure_ascii=False, indent=2)}")
            return parsed
        except json.JSONDecodeError:
            print(f"<<< 응답 (텍스트): {response}")
            return response
    else:
        print("<<< 응답 없음")
        return None

def main():
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='MCP 서버 테스트')
    parser.add_argument('--data-path', default='.', help='데이터 디렉토리 경로 (기본값: 현재 디렉토리)')
    parser.add_argument('--script-path', default='stylebook_mcp_fastmcp.py', help='MCP 서버 스크립트 경로')
    parser.add_argument('--query', default='날짜', help='테스트 검색어')
    parser.add_argument('--rule-id', default='ST-JUDGE-WRITINGPRINCIPLE-TIMEDATE-001', help='테스트할 규칙 ID')
    
    args = parser.parse_args()
    
    # 스크립트 경로가 존재하는지 확인
    if not os.path.exists(args.script_path):
        print(f"오류: 스크립트 파일을 찾을 수 없습니다: {args.script_path}")
        return
    
    # MCP 서버 실행
    cmd = ["python", "-u", args.script_path, "--stdio", "--verbose", "--data_path", args.data_path]
    print(f"MCP 서버 실행: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # 서버 출력 모니터링 스레드 시작
    def monitor_stderr():
        while True:
            line = process.stderr.readline()
            if not line:
                break
            print(f"[서버 로그] {line.strip()}")
    
    import threading
    monitor_thread = threading.Thread(target=monitor_stderr)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 초기화 요청
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        },
        "id": 1
    }
    
    init_response = send_request(process, init_request)
    
    if not init_response:
        print("초기화 실패. 서버 오류를 확인하세요.")
        process.terminate()
        return
    
    # 도구 목록 요청
    tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    
    tools_response = send_request(process, tools_request)
    
    # 테스트 요청 - 메타데이터 조회
    metadata_request = {
        "jsonrpc": "2.0",
        "method": "tools/execute",
        "params": {
            "name": "get_metadata"
        },
        "id": 3
    }
    
    send_request(process, metadata_request)
    
    # 테스트 요청 - 규칙 검색
    search_request = {
        "jsonrpc": "2.0",
        "method": "tools/execute",
        "params": {
            "name": "search",
            "arguments": {
                "query": args.query
            }
        },
        "id": 4
    }
    
    send_request(process, search_request)
    
    # 테스트 요청 - 특정 규칙 조회
    rule_request = {
        "jsonrpc": "2.0",
        "method": "tools/execute",
        "params": {
            "name": "get_rule",
            "arguments": {
                "rule_id": args.rule_id
            }
        },
        "id": 5
    }
    
    send_request(process, rule_request)
    
    # 서버 종료
    print("\n서버 종료 중...")
    process.terminate()

if __name__ == "__main__":
    main() 