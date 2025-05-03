#!/usr/bin/env python
"""
스타일북 서버

이 파일은 HTTP API를 통해 스타일북 JSON 데이터를 조회하고
관리할 수 있는 서버를 제공합니다.
"""
import argparse
import json
import logging
import os
import sys
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# 비동기 HTTP 요청 라이브러리 임포트
try:
    import aiohttp
except ImportError:
    print("aiohttp 라이브러리를 설치해주세요: pip install aiohttp")
    sys.exit(1)

# Flask 라이브러리 임포트
try:
    from flask import Flask, request, jsonify, Response, send_file
except ImportError:
    print("Flask 라이브러리를 설치해주세요: pip install flask")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask 앱 생성
app = Flask(__name__)

# 전역 변수
stylebook_data = {}  # 로드된 스타일북 데이터
metadata = {}  # 메타데이터

# ---- 스미더리 MCP 엔드포인트 ----

@app.route('/.well-known/mcp/smithery.json', methods=['GET'])
def mcp_discovery():
    """스미더리 MCP 검색 엔드포인트를 제공합니다."""
    smithery_config = {
        "type": "http",
        "schema": {
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_metadata", "get_categories", "get_rule", "search", "claude_search", "download_json"],
                    "description": "실행할 도구 이름"
                },
                "rule_id": {
                    "type": "string",
                    "description": "규칙 ID (get_rule, download_json 도구용)"
                },
                "query": {
                    "type": "string",
                    "description": "검색어 (search, claude_search 도구용)"
                },
                "desktop_port": {
                    "type": "number",
                    "description": "Claude 데스크톱 앱의 통신 포트 (기본값: 5000)"
                }
            },
            "required": ["action"]
        },
        "examples": [
            {
                "action": "search",
                "query": "외래어 표기법"
            }
        ]
    }
    return jsonify(smithery_config)

# MCP API 엔드포인트
@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    """스미더리 MCP API 엔드포인트"""
    global stylebook_data
    
    data = request.json
    
    if not data:
        return jsonify({"error": "요청 데이터가 없습니다."}), 400
    
    action = data.get("action")
    if not action:
        return jsonify({"error": "action이 필요합니다."}), 400
    
    # 요청된 액션에 따라 함수 실행
    if action == "get_metadata":
        result = get_metadata_func()
    elif action == "get_categories":
        result = get_categories_func()
    elif action == "get_rule":
        result = get_rule_func(data)
    elif action == "search":
        result = search_func(data)
    elif action == "claude_search":
        # 비동기 함수 호출
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = claude_search_func(data)
        finally:
            loop.close()
    elif action == "download_json":
        result = download_json_func(data)
    else:
        return jsonify({"error": f"알 수 없는 액션: {action}"}), 400
    
    return jsonify(result)

# ---- 클로드 데스크톱 연동 ----

class ClaudeDesktopIntegration:
    """Claude 데스크톱과 직접 연동하기 위한 클래스"""
    
    def __init__(self, desktop_port=5000, desktop_url=None):
        """
        Claude 데스크톱 연동 설정
        :param desktop_port: Claude 데스크톱 앱의 통신 포트
        :param desktop_url: Claude 데스크톱 앱의 URL (기본값: http://localhost:{port})
        """
        self.desktop_port = desktop_port
        self.desktop_url = desktop_url or f"http://localhost:{desktop_port}"
        logger.info(f"Claude 데스크톱 연동 초기화: {self.desktop_url}")
    
    async def send_to_claude_desktop(self, message, timeout=60):
        """
        Claude 데스크톱에 메시지 전송
        :param message: 전송할 메시지
        :param timeout: 타임아웃 (초)
        :return: Claude의 응답
        """
        url = f"{self.desktop_url}/api/chat"
        data = {"message": message}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Claude 데스크톱 오류 (상태 코드: {response.status}): {error_text}")
                        return {"error": f"Claude 데스크톱 오류 (상태 코드: {response.status}): {error_text}"}
        except Exception as e:
            logger.error(f"Claude 데스크톱 연결 오류: {str(e)}")
            return {"error": f"Claude 데스크톱 연결 오류: {str(e)}"}
    
    async def search_stylebook(self, query):
        """
        스타일북에서 검색 수행
        :param query: 검색어
        :return: 검색 결과
        """
        prompt = f"""
        당신은 서울경제신문 스타일북 검색 엔진입니다. 
        사용자의 질의에 가장 적합한 스타일북 규칙을 찾아서 JSON 형식으로 반환해주세요.
        
        스타일북은 다음과 같은 주요 카테고리로 구성되어 있습니다:
        1. 기사작성 요령
        2. 자주 틀리는 말
        3. 문법
        4. 제목과 레이아웃
        5. 기사 작성 준칙
        6. 뉴스가치 판단
        
        결과는 다음 형식으로 반환해주세요:
        ```json
        {{
          "results": [
            {{
              "rule_id": "규칙 ID",
              "title": "규칙 제목",
              "path": "규칙 경로 (예: 자주 틀리는 말/문법)",
              "description": "규칙 설명",
              "content": "규칙 본문 또는 요약",
              "relevance": "관련성 점수 (0-10)"
            }},
            ...
          ]
        }}
        ```
        
        질의: {query}
        """
        
        logger.debug(f"Claude에 스타일북 검색 요청: {query}")
        response = await self.send_to_claude_desktop(prompt)
        
        if "error" in response:
            logger.error(f"Claude 응답 오류: {response['error']}")
            return response
        
        # Claude 응답에서 JSON 추출
        claude_response = response.get("response", "")
        json_match = re.search(r'\{[\s\S]*\}', claude_response)
        
        if json_match:
            json_str = json_match.group(0)
            try:
                json_data = json.loads(json_str)
                logger.debug(f"Claude로부터 검색 결과 성공: {len(json_str)} 바이트")
                return json_data
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {str(e)}")
                return {"error": f"JSON 파싱 오류: {str(e)}"}
        
        logger.error("Claude 응답에서 JSON을 추출할 수 없습니다")
        return {"error": "Claude 응답에서 JSON을 추출할 수 없습니다"}

# ---- 유틸리티 함수 ----

def load_stylebook_data(base_path):
    """
    스타일북 데이터 로드
    :param base_path: 스타일북 JSON 파일이 있는 기본 경로
    :return: 로드된 스타일북 데이터
    """
    data = {}
    try:
        # 메타데이터 로드
        metadata_path = os.path.join(base_path, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                data["metadata"] = metadata
        
        # 모든 카테고리 및 파일 로드
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".json") and file != "metadata.json":
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, base_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                            data[rel_path] = file_data
                            logger.debug(f"로드됨: {rel_path}")
                    except Exception as e:
                        logger.error(f"파일 로드 오류 ({file_path}): {str(e)}")
        
        logger.info(f"스타일북 데이터 로드 완료: {len(data)} 항목")
        return data
    except Exception as e:
        logger.error(f"스타일북 데이터 로드 실패: {str(e)}")
        return {}

def search_stylebook(query, data):
    """
    스타일북 데이터에서 간단한 검색 수행
    :param query: 검색어
    :param data: 스타일북 데이터
    :return: 검색 결과
    """
    results = []
    
    query = query.lower()
    
    # 메타데이터 제외하고 검색
    for path, content in data.items():
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
                
            # 태그 검색
            if "tags" in structure:
                for tag in structure["tags"]:
                    if query in tag.lower():
                        results.append({
                            "rule_id": content.get("rule_id", ""),
                            "path": path,
                            "title": structure.get("title", ""),
                            "description": structure.get("description", ""),
                            "relevance": 6
                        })
                        break
            
            # 키워드 검색
            if "keywords" in structure:
                for keyword in structure["keywords"]:
                    if query in keyword.lower():
                        results.append({
                            "rule_id": content.get("rule_id", ""),
                            "path": path,
                            "title": structure.get("title", ""),
                            "description": structure.get("description", ""),
                            "relevance": 5
                        })
                        break
    
    # 중복 제거 및 관련성 점수로 정렬
    unique_results = []
    seen_ids = set()
    
    for result in sorted(results, key=lambda x: x["relevance"], reverse=True):
        if result["rule_id"] not in seen_ids:
            unique_results.append(result)
            seen_ids.add(result["rule_id"])
    
    return {"results": unique_results}

# ---- API 엔드포인트 ----

@app.route('/config', methods=['GET'])
def get_config():
    """
    설정 정보를 반환합니다.
    """
    config = {
        "name": "서울경제신문 스타일북 서버",
        "version": "1.0.0",
        "description": "스타일북 JSON 데이터를 조회하고 관리하는 서버",
        "tools": {
            "get_metadata": {
                "description": "스타일북 메타데이터를 반환합니다.",
                "parameters": {}
            },
            "get_categories": {
                "description": "스타일북 카테고리 목록을 반환합니다.",
                "parameters": {}
            },
            "get_rule": {
                "description": "스타일북 규칙을 반환합니다.",
                "parameters": {
                    "rule_id": {
                        "type": "string",
                        "description": "규칙 ID"
                    }
                }
            },
            "search": {
                "description": "스타일북에서 검색합니다.",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "검색어"
                    }
                }
            },
            "claude_search": {
                "description": "Claude를 사용하여 스타일북에서 검색합니다.",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "검색어"
                    },
                    "desktop_port": {
                        "type": "integer",
                        "description": "Claude 데스크톱 앱의 통신 포트 (기본값: 5000)"
                    }
                }
            },
            "download_json": {
                "description": "스타일북 JSON 파일을 다운로드합니다.",
                "parameters": {
                    "rule_id": {
                        "type": "string",
                        "description": "규칙 ID (선택: 없으면 전체 데이터)"
                    }
                }
            }
        }
    }
    
    logger.debug(f"설정 정보 요청 처리됨")
    return jsonify(config)

@app.route('/tools', methods=['GET'])
def get_tools():
    """
    등록된 도구 목록을 반환합니다.
    """
    tools = {
        "tools": [
            "get_metadata", 
            "get_categories", 
            "get_rule", 
            "search", 
            "claude_search", 
            "download_json"
        ]
    }
    
    logger.debug(f"도구 목록 요청 처리됨")
    return jsonify(tools)

# ---- 툴 엔드포인트 ----

@app.route('/tools/get_metadata', methods=['GET', 'POST'])
def get_metadata_endpoint():
    """
    스타일북 메타데이터를 반환합니다.
    """
    global stylebook_data
    
    if "metadata" not in stylebook_data:
        return jsonify({"success": False, "message": "메타데이터를 찾을 수 없습니다."})
    
    return jsonify({
        "success": True,
        "metadata": stylebook_data["metadata"]
    })

@app.route('/tools/get_categories', methods=['GET', 'POST'])
def get_categories_endpoint():
    """
    스타일북 카테고리 목록을 반환합니다.
    """
    global stylebook_data
    
    if "metadata" not in stylebook_data:
        return jsonify({"success": False, "message": "메타데이터를 찾을 수 없습니다."})
    
    categories = stylebook_data["metadata"].get("structure", {}).get("categories", [])
    
    return jsonify({
        "success": True,
        "categories": categories
    })

@app.route('/tools/get_rule', methods=['POST'])
def get_rule_endpoint():
    """
    스타일북 규칙을 반환합니다.
    """
    global stylebook_data
    
    data = request.json or {}
    rule_id = data.get("rule_id")
    
    if not rule_id:
        return jsonify({"success": False, "message": "rule_id가 필요합니다."})
    
    # 모든 파일에서 해당 rule_id 검색
    for path, content in stylebook_data.items():
        if path == "metadata":
            continue
            
        if content.get("rule_id") == rule_id:
            return jsonify({
                "success": True,
                "rule": content,
                "path": path
            })
    
    return jsonify({"success": False, "message": f"규칙을 찾을 수 없습니다: {rule_id}"})

@app.route('/tools/search', methods=['POST'])
def search_endpoint():
    """
    스타일북에서 검색합니다.
    """
    global stylebook_data
    
    data = request.json or {}
    query = data.get("query")
    
    if not query:
        return jsonify({"success": False, "message": "query가 필요합니다."})
    
    # 검색 수행
    results = search_stylebook(query, stylebook_data)
    
    return jsonify({
        "success": True,
        "query": query,
        "results": results["results"]
    })

@app.route('/tools/claude_search', methods=['POST'])
async def claude_search_endpoint():
    """
    Claude를 사용하여 스타일북에서 검색합니다.
    """
    global stylebook_data
    
    data = request.json or {}
    query = data.get("query")
    desktop_port = data.get("desktop_port", 5000)
    
    if not query:
        return jsonify({"success": False, "message": "query가 필요합니다."})
    
    # Claude 데스크톱 연동 초기화
    claude_integration = ClaudeDesktopIntegration(desktop_port=desktop_port)
    
    # 비동기 함수 호출을 위한 이벤트 루프 사용
    import asyncio
    
    try:
        # 이벤트 루프 가져오기
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # 이벤트 루프가 없는 경우 새로 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Claude로 검색 수행
    search_results = loop.run_until_complete(claude_integration.search_stylebook(query))
    
    if isinstance(search_results, dict) and "error" in search_results:
        return jsonify({"success": False, "message": search_results["error"]})
    
    return jsonify({
        "success": True,
        "query": query,
        "results": search_results.get("results", [])
    })

@app.route('/tools/download_json', methods=['GET', 'POST'])
def download_json_endpoint():
    """
    스타일북 JSON 파일을 다운로드합니다.
    """
    global stylebook_data
    
    # POST 요청이면 JSON에서 rule_id 추출, GET 요청이면 query parameter에서 추출
    if request.method == 'POST':
        data = request.json or {}
        rule_id = data.get("rule_id")
    else:
        rule_id = request.args.get("rule_id")
    
    # rule_id가 없으면 전체 데이터 반환
    if not rule_id:
        # 임시 파일 생성
        temp_file = f"/tmp/stylebook_data_{uuid.uuid4()}.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(stylebook_data, f, ensure_ascii=False, indent=2)
        
        return send_file(temp_file, as_attachment=True, download_name="stylebook_data.json")
    
    # 특정 rule_id에 해당하는 파일 찾기
    for path, content in stylebook_data.items():
        if path == "metadata":
            continue
            
        if content.get("rule_id") == rule_id:
            # 임시 파일 생성
            temp_file = f"/tmp/{rule_id}_{uuid.uuid4()}.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            filename = os.path.basename(path)
            return send_file(temp_file, as_attachment=True, download_name=filename)
    
    return jsonify({"success": False, "message": f"규칙을 찾을 수 없습니다: {rule_id}"})

# ---- 스미더리 연동을 위한 표준 입출력 모드 ----

def handle_stdio_mode():
    """
    표준 입출력 모드로 MCP를 실행합니다.
    
    이 함수는 표준 입력에서 JSON 요청을 읽고 표준 출력으로 응답을 전송합니다.
    스미더리와 같은 도구와의 통합을 위해 사용됩니다.
    """
    logger.info("표준 입출력 모드로 실행 중입니다.")
    
    # 도구 및 기능 목록
    tools = {
        "get_metadata": lambda params: get_metadata_func(),
        "get_categories": lambda params: get_categories_func(),
        "get_rule": lambda params: get_rule_func(params),
        "search": lambda params: search_func(params),
        "claude_search": lambda params: claude_search_func(params),
        "download_json": lambda params: download_json_func(params)
    }
    
    while True:
        try:
            # 표준 입력에서 JSON 읽기
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line)
            logger.debug(f"요청 받음: {request}")
            
            # 요청 처리
            response = process_request(request, tools)
            
            # 응답 전송
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            
        except json.JSONDecodeError as e:
            error_response = {"error": f"유효하지 않은 JSON: {str(e)}"}
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            import traceback
            error_response = {"error": f"처리 중 오류 발생: {str(e)}", "traceback": traceback.format_exc()}
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()

def process_request(request, tools):
    """
    요청을 처리합니다.
    
    Args:
        request: 요청 객체
        tools: 도구 함수 딕셔너리
        
    Returns:
        처리 결과
    """
    if not isinstance(request, dict):
        return {"error": "요청은 딕셔너리 형태여야 합니다."}
    
    tool_name = request.get("tool")
    params = request.get("parameters", {})
    
    if not tool_name:
        return {"error": "tool 필드가 필요합니다."}
    
    if tool_name not in tools:
        available_tools = list(tools.keys())
        return {"error": f"알 수 없는 도구: {tool_name}", "available_tools": available_tools}
    
    try:
        result = tools[tool_name](params)
        return {"result": result}
    except Exception as e:
        import traceback
        return {"error": f"도구 실행 오류: {str(e)}", "traceback": traceback.format_exc()}

# 도구 기능 구현
def get_metadata_func():
    """스타일북 메타데이터를 반환합니다."""
    global stylebook_data
    
    if "metadata" not in stylebook_data:
        return {"success": False, "message": "메타데이터를 찾을 수 없습니다."}
    
    return {
        "success": True,
        "metadata": stylebook_data["metadata"]
    }

def get_categories_func():
    """스타일북 카테고리 목록을 반환합니다."""
    global stylebook_data
    
    if "metadata" not in stylebook_data:
        return {"success": False, "message": "메타데이터를 찾을 수 없습니다."}
    
    categories = stylebook_data["metadata"].get("structure", {}).get("categories", [])
    
    return {
        "success": True,
        "categories": categories
    }

def get_rule_func(params):
    """스타일북 규칙을 반환합니다."""
    global stylebook_data
    
    rule_id = params.get("rule_id")
    
    if not rule_id:
        return {"success": False, "message": "rule_id가 필요합니다."}
    
    # 모든 파일에서 해당 rule_id 검색
    for path, content in stylebook_data.items():
        if path == "metadata":
            continue
            
        if content.get("rule_id") == rule_id:
            return {
                "success": True,
                "rule": content,
                "path": path
            }
    
    return {"success": False, "message": f"규칙을 찾을 수 없습니다: {rule_id}"}

def search_func(params):
    """스타일북에서 검색합니다."""
    global stylebook_data
    
    query = params.get("query")
    
    if not query:
        return {"success": False, "message": "query가 필요합니다."}
    
    # 검색 수행
    results = search_stylebook(query, stylebook_data)
    
    return {
        "success": True,
        "query": query,
        "results": results["results"]
    }

def claude_search_func(params):
    """Claude를 사용하여 스타일북에서 검색합니다."""
    query = params.get("query")
    desktop_port = int(params.get("desktop_port", 5000))
    
    if not query:
        return {"success": False, "message": "query가 필요합니다."}
    
    # Claude 데스크톱 연동 초기화
    claude_integration = ClaudeDesktopIntegration(desktop_port=desktop_port)
    
    # 비동기 함수 호출을 위한 이벤트 루프 사용
    import asyncio
    
    try:
        # 이벤트 루프 가져오기
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # 이벤트 루프가 없는 경우 새로 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Claude로 검색 수행
    search_results = loop.run_until_complete(claude_integration.search_stylebook(query))
    
    if isinstance(search_results, dict) and "error" in search_results:
        return {"success": False, "message": search_results["error"]}
    
    return {
        "success": True,
        "query": query,
        "results": search_results.get("results", [])
    }

def download_json_func(params):
    """스타일북 JSON 파일을 다운로드합니다."""
    global stylebook_data
    
    rule_id = params.get("rule_id")
    
    # rule_id가 없으면 전체 데이터 반환
    if not rule_id:
        return {
            "success": True,
            "data": stylebook_data,
            "message": "전체 스타일북 데이터"
        }
    
    # 특정 rule_id에 해당하는 파일 찾기
    for path, content in stylebook_data.items():
        if path == "metadata":
            continue
            
        if content.get("rule_id") == rule_id:
            return {
                "success": True,
                "data": content,
                "path": path,
                "message": f"규칙 데이터: {rule_id}"
            }
    
    return {"success": False, "message": f"규칙을 찾을 수 없습니다: {rule_id}"}

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='서울경제신문 스타일북 서버')
    parser.add_argument('--host', default='0.0.0.0', help='서버 호스트')
    parser.add_argument('--port', type=int, default=5012, help='서버 포트')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
    parser.add_argument('--stdio', action='store_true', help='표준 입출력 모드')
    parser.add_argument('--verbose', action='store_true', help='자세한 로깅')
    parser.add_argument('--data_path', default='.', help='스타일북 데이터 경로')
    
    args = parser.parse_args()
    
    # 로그 레벨 설정
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # 스타일북 데이터 로드
    global stylebook_data
    stylebook_data = load_stylebook_data(args.data_path)
    
    if args.stdio:
        # 표준 입출력 모드
        handle_stdio_mode()
    else:
        # HTTP 서버 모드
        print(f"서울경제신문 스타일북 서버 시작 중... (http://{args.host}:{args.port}/)")
        app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()