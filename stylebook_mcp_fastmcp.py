#!/usr/bin/env python
"""
스타일북 MCP 서버 - FastMCP SDK 버전

이 파일은 스타일북 데이터를 조회하고 검색할 수 있는 MCP 서버를 제공합니다.
FastMCP SDK를 사용하여 더 간결하게 구현되었습니다.
"""
import argparse
import json
import logging
import os
import sys
import time
import threading
import psutil
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("MCP SDK를 설치해주세요: pip install mcp[cli]", file=sys.stderr)
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("aiohttp 라이브러리를 설치해주세요: pip install aiohttp", file=sys.stderr)
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # 로그를 stderr로 출력
)
logger = logging.getLogger(__name__)

# 전역 변수
DATA_PATH = '.'  # 기본 데이터 경로
stylebook_data = {}  # 로드된 스타일북 데이터
start_time = time.time()  # 서버 시작 시간

# 스크립트 파일의 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# MCP 서버 인스턴스 생성
mcp = FastMCP(
    name="서울경제신문 스타일북",
    version="1.0.0",
    description="스타일북 검색 및 조회 MCP 서버"
)

# ---- 유틸리티 함수 ----

def resolve_path(path):
    """
    경로 문자열을 절대 경로로 변환합니다.
    상대 경로는 스크립트 파일이 있는 디렉토리를 기준으로 합니다.
    """
    if os.path.isabs(path):
        return path
    
    # 현재 작업 디렉토리 기준 상대 경로
    cwd_path = os.path.abspath(path)
    
    # 스크립트 디렉토리 기준 상대 경로
    script_path = os.path.join(SCRIPT_DIR, path)
    
    # 두 경로 중 존재하는 경로 반환
    if os.path.exists(cwd_path):
        return cwd_path
    elif os.path.exists(script_path):
        return script_path
    else:
        # 존재하지 않는 경우 작업 디렉토리 기준 반환
        return cwd_path

def load_stylebook_data(base_path):
    """
    스타일북 데이터 로드
    :param base_path: 스타일북 JSON 파일이 있는 기본 경로
    :return: 로드된 스타일북 데이터
    """
    # 경로 확인 및 변환
    resolved_path = resolve_path(base_path)
    logger.info(f"데이터 로드 경로: {resolved_path} (원본 경로: {base_path})")
    
    data = {}
    try:
        # 메타데이터 로드
        metadata_path = os.path.join(resolved_path, "metadata.json")
        if not os.path.exists(metadata_path):
            # _meta.json도 확인
            metadata_path = os.path.join(resolved_path, "_meta.json")
            
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                data["metadata"] = metadata
                logger.info(f"메타데이터 로드됨: {metadata_path}")
        else:
            logger.warning(f"메타데이터 파일이 없습니다. 다음 위치에서 찾아봤습니다: {os.path.join(resolved_path, 'metadata.json')}, {os.path.join(resolved_path, '_meta.json')}")
        
        # 모든 카테고리 및 파일 로드
        file_count = 0
        for root, dirs, files in os.walk(resolved_path):
            # .git 등 숨김 디렉토리 제외
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.endswith(".json") and file not in ["metadata.json", "_meta.json"]:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, resolved_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                            data[rel_path] = file_data
                            file_count += 1
                            logger.debug(f"파일 로드됨: {rel_path}")
                    except Exception as e:
                        logger.error(f"파일 로드 오류 ({file_path}): {str(e)}")
        
        logger.info(f"스타일북 데이터 로드 완료: {file_count}개 파일, 총 {len(data)} 항목")
        return data
    except Exception as e:
        logger.error(f"스타일북 데이터 로드 실패: {str(e)}")
        return {}

def get_server_stats():
    """
    서버 상태 정보를 수집합니다.
    """
    uptime = time.time() - start_time
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{int(hours)}시간 {int(minutes)}분 {int(seconds)}초"
    
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss / (1024 * 1024)  # MB 단위
    
    return {
        "uptime": uptime_str,
        "memory_usage": f"{memory_usage:.2f} MB",
        "pid": os.getpid(),
        "data_path": resolve_path(DATA_PATH),
        "python_version": sys.version
    }

# ---- MCP 프로토콜 메서드 ----

@mcp.route("resources/list")
def handle_resources_list():
    """
    MCP 프로토콜의 resources/list 메서드 구현
    """
    logger.debug("resources/list 메서드 호출됨")
    return {"resources": []}

@mcp.route("prompts/list")
def handle_prompts_list():
    """
    MCP 프로토콜의 prompts/list 메서드 구현
    """
    logger.debug("prompts/list 메서드 호출됨")
    return {"prompts": []}

@mcp.route("debug/status")
def debug_status():
    """
    서버 상태 디버깅 정보를 제공하는 엔드포인트
    """
    global stylebook_data
    logger.debug("debug/status 메서드 호출됨")
    
    stats = get_server_stats()
    
    return {
        "loaded_data_count": len(stylebook_data),
        "server_uptime": stats["uptime"],
        "memory_usage": stats["memory_usage"],
        "pid": stats["pid"],
        "data_path": stats["data_path"],
        "python_version": stats["python_version"],
        "categories": list(stylebook_data.keys())[:5] + ["..."] if len(stylebook_data) > 5 else list(stylebook_data.keys())
    }

# ---- 도구 구현 ----

@mcp.tool()
def get_metadata() -> Dict:
    """
    스타일북 메타데이터를 반환합니다.
    """
    global stylebook_data
    logger.debug("메타데이터 조회 함수 호출")
    
    if "metadata" not in stylebook_data:
        return {"error": "메타데이터를 찾을 수 없습니다."}
    
    return {"metadata": stylebook_data["metadata"]}

@mcp.tool()
def get_categories() -> Dict:
    """
    스타일북 카테고리 목록을 반환합니다.
    """
    global stylebook_data
    logger.debug("카테고리 목록 조회 함수 호출")
    
    if "metadata" not in stylebook_data:
        return {"error": "메타데이터를 찾을 수 없습니다."}
    
    categories = stylebook_data["metadata"].get("structure", {}).get("categories", [])
    
    return {"categories": categories}

@mcp.tool()
def get_rule(rule_id: str) -> Dict:
    """
    스타일북 규칙을 반환합니다.
    
    :param rule_id: 규칙 ID
    """
    global stylebook_data
    logger.debug(f"규칙 조회 함수 호출: {rule_id}")
    
    if not rule_id:
        return {"error": "규칙 ID가 필요합니다."}
    
    # 모든 파일에서 해당 rule_id 검색
    for path, content in stylebook_data.items():
        if path == "metadata":
            continue
            
        if content.get("rule_id") == rule_id:
            return {
                "rule": content,
                "path": path
            }
    
    return {"error": f"규칙을 찾을 수 없습니다: {rule_id}"}

@mcp.tool()
def search(query: str) -> Dict:
    """
    키워드로 스타일북을 검색합니다.
    
    :param query: 검색어
    """
    global stylebook_data
    logger.debug(f"검색 함수 호출: {query}")
    
    if not query:
        return {"error": "검색어가 필요합니다."}
    
    results = []
    query = query.lower()
    
    # 메타데이터 제외하고 검색
    for path, content in stylebook_data.items():
        if path == "metadata":
            continue
            
        # 규칙 ID, 제목, 설명 등에서 검색
        if "rule_id" in content and query in content["rule_id"].lower():
            results.append({
                "rule_id": content["rule_id"],
                "path": path,
                "title": content.get("versions", [{}])[0].get("structure", {}).get("title", ""),
                "description": content.get("versions", [{}])[0].get("structure", {}).get("description", ""),
                "relevance": 8
            })
            continue
            
        # 버전 및 구조 정보 검색
        for version in content.get("versions", []):
            structure = version.get("structure", {})
            
            # 제목 검색
            if "title" in structure and query in structure["title"].lower():
                results.append({
                    "rule_id": content.get("rule_id", ""),
                    "path": path,
                    "title": structure["title"],
                    "description": structure.get("description", ""),
                    "relevance": 9
                })
                continue
                
            # 설명 검색
            if "description" in structure and query in structure["description"].lower():
                results.append({
                    "rule_id": content.get("rule_id", ""),
                    "path": path,
                    "title": structure.get("title", ""),
                    "description": structure["description"],
                    "relevance": 7
                })
                continue
    
    # 중복 제거 및 관련성 점수로 정렬
    unique_results = []
    seen_ids = set()
    
    for result in sorted(results, key=lambda x: x["relevance"], reverse=True):
        if result["rule_id"] not in seen_ids:
            unique_results.append(result)
            seen_ids.add(result["rule_id"])
    
    logger.info(f"검색 결과: {len(unique_results)}개 항목 발견")
    return {"results": unique_results}

@mcp.tool()
async def claude_search(query: str, desktop_port: int = 5000) -> Dict:
    """
    Claude AI를 사용하여 스타일북을 검색합니다.
    
    :param query: 검색어
    :param desktop_port: Claude 데스크톱 앱의 통신 포트 (기본값: 5000)
    """
    logger.debug(f"Claude 검색 함수 호출: {query}, 포트: {desktop_port}")
    
    if not query:
        return {"error": "검색어가 필요합니다."}
    
    # Claude Desktop API에 연결
    claude_url = f"http://localhost:{desktop_port}/api/chat"
    
    prompt = f"""
    당신은 서울경제신문 스타일북 검색 엔진입니다. 
    사용자의 질의에 가장 적합한 스타일북 규칙을 찾아서 JSON 형식으로 반환해주세요.
    
    결과는 다음 형식으로 반환해주세요:
    ```json
    {{
      "results": [
        {{
          "rule_id": "규칙 ID",
          "title": "규칙 제목",
          "description": "규칙 설명",
          "relevance": "관련성 점수 (0-10)"
        }},
        ...
      ]
    }}
    ```
    
    질의: {query}
    """
    
    message = {
        "message": prompt,
        "model": "claude-3-opus-20240229"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(claude_url, json=message) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Claude 응답에서 JSON 추출
                    claude_response = result.get("response", "")
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', claude_response)
                    
                    if json_match:
                        json_str = json_match.group(0)
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON 파싱 오류: {str(e)}")
                            return {"error": f"JSON 파싱 오류: {str(e)}"}
                    
                    return {"error": "Claude 응답에서 JSON을 추출할 수 없습니다"}
                else:
                    error_text = await response.text()
                    logger.error(f"Claude 데스크톱 오류 (상태 코드: {response.status}): {error_text}")
                    return {"error": f"Claude 데스크톱 오류 (상태 코드: {response.status})"}
    except Exception as e:
        logger.error(f"Claude 데스크톱 연결 오류: {str(e)}")
        return {"error": f"Claude 데스크톱 연결 오류: {str(e)}"}

@mcp.tool()
def download_json(rule_id: Optional[str] = None) -> Dict:
    """
    스타일북 JSON 파일을 다운로드합니다.
    
    :param rule_id: 규칙 ID (선택: 없으면 전체 데이터)
    """
    global stylebook_data
    logger.debug(f"JSON 다운로드 함수 호출: {rule_id if rule_id else '전체'}")
    
    # rule_id가 없으면 전체 데이터 반환
    if not rule_id:
        return {"full_data": stylebook_data}
    
    # 특정 rule_id에 해당하는 파일 찾기
    for path, content in stylebook_data.items():
        if path == "metadata":
            continue
            
        if content.get("rule_id") == rule_id:
            return {"rule_data": content, "path": path}
    
    return {"error": f"규칙을 찾을 수 없습니다: {rule_id}"}

# ---- 로그 모니터링 스레드 ----

def log_monitor_thread():
    """
    서버 로그를 주기적으로 모니터링하고 상태를 기록하는 스레드
    """
    while True:
        stats = get_server_stats()
        loaded_data_count = len(stylebook_data) if stylebook_data else 0
        
        logger.info(f"서버 상태: 업타임={stats['uptime']}, 메모리={stats['memory_usage']}, 로드된 데이터={loaded_data_count}개")
        time.sleep(300)  # 5분마다 상태 로깅

# ---- 메인 함수 ----

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='서울경제신문 스타일북 서버 (FastMCP)')
    parser.add_argument('--stdio', action='store_true', help='표준 입출력 모드로 실행')
    parser.add_argument('--http', action='store_true', help='HTTP 모드로 실행')
    parser.add_argument('--port', type=int, default=5012, help='HTTP 모드 포트 번호')
    parser.add_argument('--host', default='0.0.0.0', help='HTTP 모드 호스트')
    parser.add_argument('--data_path', default='.', help='스타일북 데이터 경로')
    parser.add_argument('--verbose', action='store_true', help='자세한 로깅')
    
    args = parser.parse_args()
    
    # 로그 레벨 설정
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # 전역 변수 설정
    global DATA_PATH
    DATA_PATH = args.data_path
    logger.info(f"스타일북 데이터 경로: {DATA_PATH}")
    
    # 데이터 로드 (비동기적으로)
    def load_data():
        global stylebook_data
        stylebook_data = load_stylebook_data(args.data_path)
        
        # 데이터가 없으면 데이터 경로 자동 탐색
        if not stylebook_data:
            logger.warning(f"지정된 경로 {args.data_path}에서 데이터를 찾을 수 없습니다. 다른 경로를 탐색합니다.")
            
            # 가능한 데이터 디렉토리 목록
            possible_dirs = [
                "기사 작성 준칙",
                "기사작성 요령",
                "자주 틀리는 말",
                "제목과 레이아웃_제목달기",
                "제목과 레이아웃_레이아웃 요령",
                "기사 작성 준칙",
                "뉴스가치 판단"
            ]
            
            # 가능한 디렉토리 확인
            for dir_name in possible_dirs:
                # 스크립트 디렉토리 기준 확인
                check_path = os.path.join(SCRIPT_DIR, dir_name)
                if os.path.exists(check_path) and os.path.isdir(check_path):
                    logger.info(f"데이터 경로 자동 탐색: {check_path}")
                    stylebook_data = load_stylebook_data(check_path)
                    if stylebook_data:
                        break
            
            # 그래도 데이터가 없으면 경고
            if not stylebook_data:
                logger.warning("데이터를 찾을 수 없습니다. 빈 데이터로 시작합니다.")
    
    # 데이터 로드 스레드 시작
    data_thread = threading.Thread(target=load_data)
    data_thread.daemon = True
    data_thread.start()
    
    # 로그 모니터링 스레드 시작
    log_thread = threading.Thread(target=log_monitor_thread)
    log_thread.daemon = True
    log_thread.start()
    
    # 기본 데이터 구조 초기화 (서버 즉시 응답 가능하도록)
    if not stylebook_data:
        stylebook_data["metadata"] = {"name": "서울경제신문 스타일북", "version": "1.0.0"}
    
    if args.http:
        # HTTP 모드로 실행
        logger.info(f"HTTP 모드로 시작합니다 (http://{args.host}:{args.port})...")
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        # 표준 입출력 모드 (기본)
        logger.info("표준 입출력 모드로 시작합니다...")
        mcp.run(transport="stdio")

if __name__ == "__main__":
    logger.info("스타일북 MCP 서버 (FastMCP) 시작")
    main() 