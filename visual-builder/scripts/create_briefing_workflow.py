#!/usr/bin/env python3
"""
Daily Investment News Briefing Workflow Creator and Runner

This script:
1. Registers/logs in to get a JWT token
2. Creates a workflow with 5 nodes (Trigger -> Agent -> Multi-Agent -> Agent -> MCP Tool)
3. Runs the workflow
4. Polls execution status until completion
5. Prints the results
"""

import httpx
import json
import sys
import time
from datetime import datetime

BASE = "http://localhost:8000/api"
TIMEOUT = 180  # 3 minutes max polling


def register_and_login():
    """Register (if needed) and login to get JWT token."""
    print("🔐 Authenticating...")

    # Try to register (ignore 409 conflict if user exists)
    try:
        httpx.post(
            f"{BASE}/auth/register",
            json={
                "email": "briefing@demo.com",
                "password": "Briefing1234!",
                "name": "Briefing Demo"
            },
            follow_redirects=True,
            timeout=10
        )
        print("✓ User registered")
    except Exception as e:
        print(f"  (Registration skipped: {e})")

    # Login
    try:
        r = httpx.post(
            f"{BASE}/auth/login",
            json={
                "email": "briefing@demo.com",
                "password": "Briefing1234!"
            },
            follow_redirects=True,
            timeout=10
        )
        r.raise_for_status()
        token_data = r.json()
        token = token_data.get("token") or token_data.get("accessToken")
        if not token:
            print(f"❌ Login response missing token: {token_data}")
            sys.exit(1)
        print("✓ Logged in successfully")
        return token
    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)


def create_workflow(token):
    """Create the Daily Investment News Briefing workflow."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("\n📝 Creating workflow...")

    nodes = [
        {
            "id": "trigger",
            "type": "trigger",
            "data": {
                "triggerType": "cron",
                "cronExpression": "0 9 * * *"
            },
            "position": {"x": 100, "y": 300}
        },
        {
            "id": "query-gen",
            "type": "agent",
            "data": {
                "name": "뉴스 쿼리 생성기",
                "role": "coordinator",
                "model": "gemini-2.0-flash",
                "temperature": 0.3,
                "maxTokens": 2048,
                "systemPrompt": "당신은 금융 뉴스 리서치 코디네이터입니다. 오늘 날짜 기준으로 다음 관심 기업들에 대한 최신 뉴스와 투자 정보를 조사하기 위한 검색 쿼리를 생성하세요.\n\n관심 기업: 테슬라(TSLA), 엔비디아(NVDA), 삼성전자\n\n각 기업별로 영어 검색 쿼리를 생성하세요. 주가, 실적, 주요 이슈를 포함하세요. 반드시 입력에 포함된 오늘 날짜 연도를 검색 쿼리에 사용하세요.\n\n반드시 아래 JSON 형식으로 출력하세요:\n{\"queries\": [{\"company\": \"테슬라\", \"ticker\": \"TSLA\", \"search_query\": \"Tesla TSLA stock price news today 2026\"}, ...]}",
                "inputTemplate": "오늘 날짜: {{today}}\n\n{{input}}"
            },
            "position": {"x": 400, "y": 300}
        },
        {
            "id": "news-team",
            "type": "multi_agent",
            "data": {
                "name": "뉴스 리서치팀",
                "strategy": "map_reduce",
                "maxRounds": 5,
                "costBudget": 0.1,
                "inputTemplate": "오늘 날짜: {{today}}\n\n이전 노드 결과:\n{{query-gen}}",
                "members": [
                    {
                        "name": "coordinator",
                        "role": "coordinator",
                        "model": "gemini-2.0-flash",
                        "temperature": 0.3,
                        "systemPrompt": "당신은 투자 뉴스 리서치팀의 코디네이터입니다. 각 리서처에게 담당 기업의 최신 뉴스를 조사하도록 지시하세요. web_search 도구를 사용하여 실시간 뉴스를 검색하도록 안내하세요. 결과를 종합하여 기업별 뉴스 요약을 한국어로 정리하세요. 각 기업에 대해 sentiment(긍정/부정/중립)와 핵심 포인트를 포함하세요. 결과를 종합할 때 각 기업별 뉴스의 출처 URL 목록도 포함하세요.",
                        "mcpTools": [],
                        "capabilities": ["delegation", "synthesis"]
                    },
                    {
                        "name": "tesla-researcher",
                        "role": "worker",
                        "model": "gemini-2.0-flash",
                        "temperature": 0.5,
                        "systemPrompt": "당신은 테슬라(TSLA) 전문 리서처입니다. web_search 도구를 사용하여 테슬라의 최신 뉴스, 주가 동향, 실적 정보를 검색하세요. 검색 결과를 한국어로 요약하세요. 핵심 포인트 3개와 전반적 sentiment(긍정/부정/중립)를 판단하세요. 검색 결과의 출처 URL도 반드시 포함하세요. 각 뉴스 항목의 URL을 기록해두세요.",
                        "mcpTools": ["web-search"],
                        "capabilities": ["research", "analysis"]
                    },
                    {
                        "name": "nvidia-researcher",
                        "role": "worker",
                        "model": "gemini-2.0-flash",
                        "temperature": 0.5,
                        "systemPrompt": "당신은 엔비디아(NVDA) 전문 리서처입니다. web_search 도구를 사용하여 엔비디아의 최신 뉴스, 주가 동향, AI 산업 관련 소식을 검색하세요. 검색 결과를 한국어로 요약하세요. 핵심 포인트 3개와 전반적 sentiment(긍정/부정/중립)를 판단하세요. 검색 결과의 출처 URL도 반드시 포함하세요. 각 뉴스 항목의 URL을 기록해두세요.",
                        "mcpTools": ["web-search"],
                        "capabilities": ["research", "analysis"]
                    },
                    {
                        "name": "samsung-researcher",
                        "role": "worker",
                        "model": "gemini-2.0-flash",
                        "temperature": 0.5,
                        "systemPrompt": "당신은 삼성전자 전문 리서처입니다. web_search 도구를 사용하여 삼성전자의 최신 뉴스, 주가 동향, 반도체 산업 관련 소식을 검색하세요. 검색 결과를 한국어로 요약하세요. 핵심 포인트 3개와 전반적 sentiment(긍정/부정/중립)를 판단하세요. 검색 결과의 출처 URL도 반드시 포함하세요. 각 뉴스 항목의 URL을 기록해두세요.",
                        "mcpTools": ["web-search"],
                        "capabilities": ["research", "analysis"]
                    }
                ]
            },
            "position": {"x": 800, "y": 300}
        },
        {
            "id": "formatter",
            "type": "agent",
            "data": {
                "name": "리포트 포맷터",
                "role": "editor",
                "model": "gemini-2.0-flash",
                "temperature": 0.2,
                "maxTokens": 4096,
                "systemPrompt": "당신은 투자 리포트 편집자입니다. 입력된 뉴스 리서치 결과를 아래 JSON 형식으로 변환하세요.\n\n출력 형식 (반드시 유효한 JSON만 출력):\n{\"title\": \"일일 투자 브리핑 - YYYY-MM-DD\", \"sections_json\": \"[{\\\"heading\\\": \\\"기업명\\\", \\\"content\\\": \\\"뉴스 요약 내용...\\\", \\\"sentiment\\\": \\\"긍정\\\", \\\"key_points\\\": [\\\"포인트1\\\", \\\"포인트2\\\", \\\"포인트3\\\"], \\\"sources\\\": [{\\\"title\\\": \\\"기사 제목\\\", \\\"url\\\": \\\"https://...\\\"}]}]\"}\n\n규칙:\n1. 모든 내용은 한국어로 작성\n2. sentiment는 반드시 \"긍정\", \"부정\", \"중립\" 중 하나\n3. sections_json은 JSON 배열의 문자열 형태여야 함 (이스케이프된 JSON 문자열)\n4. 각 기업의 content는 2-3문단, key_points는 3개씩\n5. title의 날짜는 입력에 포함된 오늘 날짜를 사용하세요\n6. JSON 외 다른 텍스트를 출력하지 마세요\n7. sources는 각 기업의 뉴스 출처 URL 목록입니다. 입력 데이터에서 URL을 추출하여 포함하세요.",
                "inputTemplate": "오늘 날짜: {{today}}\n\n뉴스 리서치 결과:\n{{news-team.output}}",
                "outputFields": [
                    {"name": "title", "type": "text"},
                    {"name": "sections_json", "type": "text"}
                ]
            },
            "position": {"x": 1200, "y": 300}
        },
        {
            "id": "pdf-gen",
            "type": "mcp_tool",
            "data": {
                "serverId": "6e33baae-d325-4602-80b3-44c283022265",
                "serverName": "PDF Generator",
                "toolName": "generate_briefing_pdf",
                "description": "투자 브리핑 PDF 생성",
                "parameters": {
                    "title": "{{formatter.title}}",
                    "sections": "{{formatter.sections_json}}",
                    "footer": "AgentChord 일일 투자 브리핑 | 자동 생성 리포트"
                }
            },
            "position": {"x": 1600, "y": 300}
        },
        {
            "id": "email-send",
            "type": "mcp_tool",
            "data": {
                "serverId": "f3edb48f-4d38-4bd7-b88a-71b21fec3581",
                "serverName": "Resend Email",
                "toolName": "send-email",
                "description": "투자 브리핑 이메일 발송",
                "parameters": {
                    "to": ["soilfive0@gmail.com"],
                    "subject": "{{formatter.title}}",
                    "text": "오늘의 투자 브리핑이 PDF로 첨부되었습니다.",
                    "html": "<p>오늘의 투자 브리핑이 PDF로 첨부되었습니다. 자세한 내용은 첨부 파일을 확인해주세요.</p><p>이 이메일은 AgentChord에 의해 자동 생성되었습니다.</p>",
                    "attachments": [{"filename": "daily-briefing.pdf", "filePath": "{{pdf-gen}}"}]
                }
            },
            "position": {"x": 2000, "y": 300}
        }
    ]

    edges = [
        {"id": "e1", "source": "trigger", "target": "query-gen"},
        {"id": "e2", "source": "query-gen", "target": "news-team"},
        {"id": "e3", "source": "news-team", "target": "formatter"},
        {"id": "e4", "source": "formatter", "target": "pdf-gen"},
        {"id": "e5", "source": "pdf-gen", "target": "email-send"}
    ]

    workflow_data = {
        "name": "Daily Investment News Briefing",
        "description": "테슬라, 엔비디아, 삼성전자에 대한 일일 투자 뉴스 브리핑을 자동 생성합니다.",
        "nodes": nodes,
        "edges": edges,
        "tags": ["demo", "briefing", "multi-agent", "mcp"]
    }

    try:
        r = httpx.post(
            f"{BASE}/workflows",
            json=workflow_data,
            headers=headers,
            follow_redirects=True,
            timeout=30
        )
        r.raise_for_status()
        workflow = r.json()
        workflow_id = workflow.get("id")
        print(f"✓ Workflow created: ID={workflow_id}")
        return workflow_id
    except Exception as e:
        print(f"❌ Failed to create workflow: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
        sys.exit(1)


def run_workflow(token, workflow_id):
    """Run the workflow and return execution ID."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n🚀 Running workflow {workflow_id}...")

    run_data = {
        "input": "오늘의 투자 뉴스 브리핑을 생성해주세요.",
        "mode": "full"
    }

    try:
        r = httpx.post(
            f"{BASE}/workflows/{workflow_id}/run",
            json=run_data,
            headers=headers,
            follow_redirects=True,
            timeout=30
        )
        r.raise_for_status()
        execution = r.json()
        execution_id = execution.get("id") or execution.get("executionId")
        if not execution_id:
            print(f"❌ Execution response missing ID: {execution}")
            sys.exit(1)
        print(f"✓ Execution started: ID={execution_id}")
        return execution_id
    except Exception as e:
        print(f"❌ Failed to run workflow: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
        sys.exit(1)


def poll_execution(token, execution_id):
    """Poll execution status until completion or timeout."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n⏳ Polling execution status (max {TIMEOUT}s)...")

    start_time = time.time()
    last_status = None

    while True:
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT:
            print(f"\n❌ Timeout after {TIMEOUT}s")
            sys.exit(1)

        try:
            r = httpx.get(
                f"{BASE}/executions/{execution_id}",
                headers=headers,
                follow_redirects=True,
                timeout=10
            )
            r.raise_for_status()
            execution = r.json()

            status = execution.get("status")
            if status != last_status:
                print(f"  [{int(elapsed)}s] Status: {status}")
                last_status = status

            if status == "completed":
                print("\n✅ Execution completed successfully!")
                return execution
            elif status == "failed":
                print("\n❌ Execution failed!")
                return execution
            elif status in ["cancelled", "timeout"]:
                print(f"\n⚠️  Execution {status}")
                return execution

            # Poll every 5 seconds
            time.sleep(5)

        except Exception as e:
            print(f"⚠️  Poll error: {e}")
            time.sleep(5)


def print_results(execution):
    """Pretty-print execution results."""
    print("\n" + "="*80)
    print("EXECUTION RESULTS")
    print("="*80)

    print(f"\nExecution ID: {execution.get('id')}")
    print(f"Status: {execution.get('status')}")
    print(f"Started: {execution.get('startedAt') or execution.get('createdAt')}")
    print(f"Completed: {execution.get('completedAt')}")

    # Node results
    node_results = execution.get("nodeResults") or {}
    if node_results:
        print("\n" + "-"*80)
        print("NODE RESULTS")
        print("-"*80)

        for node_id, result in node_results.items():
            print(f"\n[{node_id}]")
            print(f"  Status: {result.get('status')}")

            output = result.get('output')
            if output:
                # Truncate very long outputs
                output_str = str(output)
                if len(output_str) > 500:
                    output_str = output_str[:500] + "... (truncated)"
                print(f"  Output: {output_str}")

            error = result.get('error')
            if error:
                print(f"  Error: {error}")

    # Final output
    final_output = execution.get("output")
    if final_output:
        print("\n" + "-"*80)
        print("FINAL OUTPUT")
        print("-"*80)
        output_str = str(final_output)
        if len(output_str) > 1000:
            output_str = output_str[:1000] + "... (truncated)"
        print(output_str)

    # Error
    error = execution.get("error")
    if error:
        print("\n" + "-"*80)
        print("ERROR")
        print("-"*80)
        print(error)

    print("\n" + "="*80)


def main():
    print("=" * 80)
    print("Daily Investment News Briefing - Workflow Creator & Runner")
    print("=" * 80)

    # Step 1: Authenticate
    token = register_and_login()

    # Step 2: Create workflow
    workflow_id = create_workflow(token)

    # Step 3: Run workflow
    execution_id = run_workflow(token, workflow_id)

    # Step 4: Poll until completion
    execution = poll_execution(token, execution_id)

    # Step 5: Print results
    print_results(execution)

    # Exit with appropriate code
    if execution.get("status") == "completed":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
