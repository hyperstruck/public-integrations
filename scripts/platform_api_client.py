#!/usr/bin/env python3
"""Small stdlib-only HTTP client for agent goals, runs, and learnings APIs.

Environment (see public_integrations/README.md):
  HYPER_BASE_URL, HYPER_AGENT_ID, HYPER_API_KEY
Optional: PUBLIC_INTEGRATIONS_ENV_FILE for a dotenv path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key, _, val = stripped.partition("=")
    key = key.strip()
    val = val.strip().strip("'").strip('"')
    if not key:
        return None
    return key, val


def load_dotenv_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Warning: could not read env file {path}: {e}", file=sys.stderr)
        return out
    for line in text.splitlines():
        parsed = _parse_dotenv_line(line)
        if parsed:
            out[parsed[0]] = parsed[1]
    return out


def resolve_api_key(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    if os.environ.get("HYPER_API_KEY"):
        return os.environ["HYPER_API_KEY"].strip()
    env_path = os.environ.get("PUBLIC_INTEGRATIONS_ENV_FILE")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path.cwd() / ".env")
    for p in candidates:
        if p.is_file():
            data = load_dotenv_file(p)
            key = data.get("HYPER_API_KEY", "").strip()
            if key:
                return key
    raise SystemExit(
        "Missing API key: set HYPER_API_KEY, pass --api-key, or add it to .env"
    )


def resolve_base_url(explicit: str | None) -> str:
    if explicit:
        return explicit.rstrip("/")
    u = os.environ.get("HYPER_BASE_URL", "").strip().rstrip("/")
    if not u:
        raise SystemExit("Missing base URL: set HYPER_BASE_URL or pass --base-url")
    return u


def resolve_agent_id(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    a = os.environ.get("HYPER_AGENT_ID", "").strip()
    if not a:
        raise SystemExit("Missing agent id: set HYPER_AGENT_ID or pass --agent-id")
    return a


def http_request(
    method: str,
    url: str,
    *,
    api_key: str,
    body: dict[str, object] | None = None,
    timeout: float = 120.0,
) -> tuple[int | None, dict | list | str | None]:
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        code = e.code
    except urllib.error.URLError as e:
        print(f"Request failed (network): {e}", file=sys.stderr)
        return None, None
    if not raw:
        return code, None
    try:
        return code, json.loads(raw)
    except json.JSONDecodeError:
        return code, raw


def _load_json_arg(raw: str | None, flag_name: str) -> dict[str, object]:
    if not raw:
        return {}
    try:
        out = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON for {flag_name}: {e}") from e
    if not isinstance(out, dict):
        raise SystemExit(f"{flag_name} must be a JSON object")
    return out


def cmd_goal_run(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    agent = resolve_agent_id(args.agent_id)
    url = f"{base}/agents/{urllib.parse.quote(agent, safe='')}/goals"
    payload: dict[str, object] = {"goal": args.goal}
    if args.context:
        payload["context"] = args.context
    if args.session_id:
        payload["session_id"] = args.session_id
    if args.worker_profile:
        payload["worker_profile"] = args.worker_profile
    if args.metadata_json:
        payload["metadata"] = _load_json_arg(args.metadata_json, "--metadata-json")
    code, body = http_request("POST", url, api_key=api_key, body=payload)
    print(json.dumps({"http_status": code, "body": body}, indent=2))
    if code is None or code >= 400:
        return 1
    run_id = None
    if isinstance(body, dict):
        run = body.get("run")
        if isinstance(run, dict):
            run_id = run.get("id")
    if run_id and not args.no_poll:
        return cmd_poll_run(
            argparse.Namespace(
                api_key=args.api_key,
                base_url=args.base_url,
                run_id=run_id,
                poll_interval=args.poll_interval,
                max_wait=args.max_wait,
            )
        )
    return 0


def cmd_poll_run(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    rid = args.run_id.strip()
    url = f"{base}/runs/{urllib.parse.quote(rid, safe='')}"
    deadline = time.monotonic() + args.max_wait
    last_status = None
    while time.monotonic() < deadline:
        code, body = http_request("GET", url, api_key=api_key)
        print(json.dumps({"http_status": code, "body": body}, indent=2))
        if code is None or code >= 400:
            return 1
        if isinstance(body, dict):
            run = body.get("run") if "run" in body else body
            if isinstance(run, dict):
                last_status = run.get("status")
        if last_status in ("completed", "failed"):
            return 0 if last_status == "completed" else 2
        if last_status == "suspended":
            print(
                "Run is suspended; human must decide and call resume "
                "(see skill platform-agent-run or POST /runs/{id}/resume).",
                file=sys.stderr,
            )
            return 3
        time.sleep(args.poll_interval)
    print("Poll timed out.", file=sys.stderr)
    return 4


def cmd_resume_run(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    rid = args.run_id.strip()
    url = f"{base}/runs/{urllib.parse.quote(rid, safe='')}/resume"
    payload: dict[str, object] = {
        "suspension_id": args.suspension_id,
        "decision_type": args.decision_type,
    }
    if args.decided_by:
        payload["decided_by"] = args.decided_by
    if args.reason:
        payload["reason"] = args.reason
    if args.worker_profile:
        payload["worker_profile"] = args.worker_profile
    if args.data_json:
        payload["data"] = _load_json_arg(args.data_json, "--data-json")
    code, body = http_request("POST", url, api_key=api_key, body=payload)
    print(json.dumps({"http_status": code, "body": body}, indent=2))
    return 1 if code is None or code >= 400 else 0


def cmd_session_messages(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    sid = args.session_id.strip()
    q = urllib.parse.urlencode({"limit": str(args.limit)})
    url = f"{base}/sessions/{urllib.parse.quote(sid, safe='')}/messages?{q}"
    code, body = http_request("GET", url, api_key=api_key)
    print(json.dumps({"http_status": code, "body": body}, indent=2))
    return 1 if code is None or code >= 400 else 0


def cmd_learnings_store(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    agent = resolve_agent_id(args.agent_id)
    url = f"{base}/agents/{urllib.parse.quote(agent, safe='')}/learnings"
    payload: dict[str, object] = {
        "content": args.content,
        "learning_type": args.learning_type,
    }
    if args.confidence is not None:
        payload["confidence"] = args.confidence
    if args.source_goal:
        payload["source_goal"] = args.source_goal
    if args.applicable_goals:
        payload["applicable_goals"] = args.applicable_goals
    if args.applicable_tools:
        payload["applicable_tools"] = args.applicable_tools
    if args.privacy:
        payload["privacy"] = args.privacy
    code, body = http_request("POST", url, api_key=api_key, body=payload)
    print(json.dumps({"http_status": code, "body": body}, indent=2))
    if code is None or code >= 400:
        return 1
    if code == 202:
        print(
            "Accepted (202): indexing is asynchronous; wait before search.",
            file=sys.stderr,
        )
    return 0


def cmd_learnings_search(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    agent = resolve_agent_id(args.agent_id)
    params: dict[str, str] = {
        "q": args.query,
        "limit": str(args.limit),
    }
    if args.min_confidence is not None:
        params["min_confidence"] = str(args.min_confidence)
    if args.learning_type:
        params["learning_type"] = args.learning_type
    if args.scope:
        params["scope"] = args.scope
    q = urllib.parse.urlencode(params)
    url = f"{base}/agents/{urllib.parse.quote(agent, safe='')}/learnings/search?{q}"
    code, body = http_request("GET", url, api_key=api_key)
    print(json.dumps({"http_status": code, "body": body}, indent=2))
    return 1 if code is None or code >= 400 else 0


def cmd_learnings_get(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    agent = resolve_agent_id(args.agent_id)
    lid = args.learning_id.strip()
    url = f"{base}/agents/{urllib.parse.quote(agent, safe='')}/learnings/{urllib.parse.quote(lid, safe='')}"
    code, body = http_request("GET", url, api_key=api_key)
    print(json.dumps({"http_status": code, "body": body}, indent=2))
    return 1 if code is None or code >= 400 else 0


def cmd_learnings_reinforce(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    base = resolve_base_url(args.base_url)
    agent = resolve_agent_id(args.agent_id)
    lid = args.learning_id.strip()
    url = f"{base}/agents/{urllib.parse.quote(agent, safe='')}/learnings/{urllib.parse.quote(lid, safe='')}/reinforce"
    payload: dict[str, object] = {"is_helpful": args.helpful}
    code, body = http_request("POST", url, api_key=api_key, body=payload)
    print(json.dumps({"http_status": code, "body": body}, indent=2))
    return 1 if code is None or code >= 400 else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Platform API helper (stdlib HTTP).")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-url", default=None, help="Override HYPER_BASE_URL")
    common.add_argument(
        "--api-key",
        default=None,
        help="Override HYPER_API_KEY (avoid passing on shared machines)",
    )

    g = sub.add_parser("goal-run", parents=[common], help="POST /agents/{id}/goals")
    g.add_argument("--agent-id", default=None, help="Override HYPER_AGENT_ID")
    g.add_argument("--goal", required=True)
    g.add_argument("--context", default=None)
    g.add_argument("--session-id", default=None)
    g.add_argument("--worker-profile", default=None)
    g.add_argument("--metadata-json", default=None)
    g.add_argument("--no-poll", action="store_true")
    g.add_argument("--poll-interval", type=float, default=2.0)
    g.add_argument("--max-wait", type=float, default=120.0)
    g.set_defaults(func=cmd_goal_run)

    pr = sub.add_parser("poll-run", parents=[common], help="GET /runs/{id} until terminal")
    pr.add_argument("--run-id", required=True)
    pr.add_argument("--interval", type=float, default=2.0, dest="poll_interval")
    pr.add_argument("--max-wait", type=float, default=120.0)
    pr.set_defaults(func=cmd_poll_run)

    rs = sub.add_parser("resume-run", parents=[common], help="POST /runs/{id}/resume")
    rs.add_argument("--run-id", required=True)
    rs.add_argument("--suspension-id", required=True)
    rs.add_argument(
        "--decision-type",
        required=True,
        help="approve|reject|modify|skip|provide_input|partial_approve",
    )
    rs.add_argument("--decided-by", default=None)
    rs.add_argument("--reason", default=None)
    rs.add_argument("--worker-profile", default=None)
    rs.add_argument("--data-json", default=None)
    rs.set_defaults(func=cmd_resume_run)

    sm = sub.add_parser(
        "session-messages", parents=[common], help="GET /sessions/{id}/messages"
    )
    sm.add_argument("--session-id", required=True)
    sm.add_argument("--limit", type=int, default=20)
    sm.set_defaults(func=cmd_session_messages)

    ls = sub.add_parser(
        "learnings-store", parents=[common], help="POST /agents/{id}/learnings"
    )
    ls.add_argument("--agent-id", default=None)
    ls.add_argument("--content", required=True)
    ls.add_argument(
        "--learning-type",
        required=True,
        help="tool_usage|approach|pitfall|prerequisite|coordination_pattern|agent_capability|conflict_insight|debate_outcome",
    )
    ls.add_argument("--confidence", type=float, default=None)
    ls.add_argument("--source-goal", default=None)
    ls.add_argument(
        "--applicable-goal",
        action="append",
        dest="applicable_goals",
        default=None,
    )
    ls.add_argument(
        "--applicable-tool",
        action="append",
        dest="applicable_tools",
        default=None,
    )
    ls.add_argument("--privacy", default=None)
    ls.set_defaults(func=cmd_learnings_store)

    lq = sub.add_parser(
        "learnings-search", parents=[common], help="GET .../learnings/search"
    )
    lq.add_argument("--agent-id", default=None)
    lq.add_argument("--query", required=True)
    lq.add_argument("--limit", type=int, default=10)
    lq.add_argument("--min-confidence", type=float, default=None)
    lq.add_argument("--learning-type", default=None)
    lq.add_argument("--scope", default=None, help="agent or org (if entitled)")
    lq.set_defaults(func=cmd_learnings_search)

    lg = sub.add_parser(
        "learnings-get", parents=[common], help="GET /agents/{id}/learnings/{learning_id}"
    )
    lg.add_argument("--agent-id", default=None)
    lg.add_argument("--learning-id", required=True)
    lg.set_defaults(func=cmd_learnings_get)

    lr = sub.add_parser(
        "learnings-reinforce",
        parents=[common],
        help="POST .../learnings/{id}/reinforce",
    )
    lr.add_argument("--agent-id", default=None)
    lr.add_argument("--learning-id", required=True)
    lr.add_argument("--helpful", action=argparse.BooleanOptionalAction, required=True)
    lr.set_defaults(func=cmd_learnings_reinforce)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
