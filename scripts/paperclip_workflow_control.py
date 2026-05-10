#!/usr/bin/env python3
"""Paperclip Workflow Control Pack.

Read-only diagnostics by default. Mutating actions require both --apply and
--confirm APPLY so installer users can preview changes before touching Paperclip.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_BASE_URL = "http://127.0.0.1:3100"


class PaperclipError(RuntimeError):
    pass


@dataclass
class Client:
    base_url: str
    token: Optional[str] = None
    timeout: float = 8.0

    @property
    def api_url(self) -> str:
        return self.base_url.rstrip("/") + "/api"

    def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        url = self.api_url + path
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise PaperclipError(f"HTTP {exc.code} {method} {path}: {raw[:500]}") from exc
        except urllib.error.URLError as exc:
            raise PaperclipError(f"Cannot reach Paperclip at {url}: {exc}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def patch(self, path: str, body: Dict[str, Any]) -> Any:
        return self.request("PATCH", path, body)

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("POST", path, body or {})

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)


def normalize_title(value: str) -> str:
    text = re.sub(r"\[[^\]]+\]", " ", value.lower())
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def status_bucket(rows: Iterable[Dict[str, Any]], key: str = "status") -> Dict[str, int]:
    out: Dict[str, int] = defaultdict(int)
    for row in rows:
        out[str(row.get(key) or "unknown")] += 1
    return dict(sorted(out.items()))


def company_filter(companies: List[Dict[str, Any]], selector: Optional[str]) -> List[Dict[str, Any]]:
    if not selector:
        return companies
    needle = selector.lower()
    selected = [c for c in companies if c.get("id") == selector or str(c.get("name", "")).lower() == needle or str(c.get("issuePrefix", "")).lower() == needle]
    if not selected:
        raise PaperclipError(f"Company not found: {selector}")
    return selected


def collect_snapshot(client: Client, company: Optional[str] = None, include_plugins: bool = True) -> Dict[str, Any]:
    health = client.get("/health")
    companies = company_filter(client.get("/companies"), company)
    company_rows = []
    totals = {
        "companies": len(companies),
        "projects": 0,
        "routines": 0,
        "activeRoutines": 0,
        "pausedRoutines": 0,
        "liveRuns": 0,
        "schedulerActiveAgents": 0,
    }

    heartbeats = []
    try:
        heartbeats = client.get("/instance/scheduler-heartbeats")
    except Exception as exc:
        heartbeats = [{"error": str(exc)}]

    for c in companies:
        cid = c["id"]
        projects = client.get(f"/companies/{urllib.parse.quote(cid)}/projects")
        routines = client.get(f"/companies/{urllib.parse.quote(cid)}/routines")
        live_runs = client.get(f"/companies/{urllib.parse.quote(cid)}/live-runs?minCount=0&limit=50")
        hb_for_company = [h for h in heartbeats if h.get("companyId") == cid]
        duplicates = find_duplicates(routines)
        row = {
            "id": cid,
            "name": c.get("name"),
            "issuePrefix": c.get("issuePrefix"),
            "projects": len(projects),
            "routines": len(routines),
            "routineStatus": status_bucket(routines),
            "liveRuns": len(live_runs),
            "schedulerAgents": len(hb_for_company),
            "schedulerActiveAgents": sum(1 for h in hb_for_company if h.get("schedulerActive")),
            "heartbeatEnabledAgents": sum(1 for h in hb_for_company if h.get("heartbeatEnabled")),
            "duplicateRoutineGroups": duplicates,
            "routinesPreview": [summarize_routine(r) for r in routines[:10]],
            "liveRunsPreview": [summarize_live_run(r) for r in live_runs[:10]],
        }
        company_rows.append(row)
        totals["projects"] += row["projects"]
        totals["routines"] += row["routines"]
        totals["activeRoutines"] += row["routineStatus"].get("active", 0)
        totals["pausedRoutines"] += row["routineStatus"].get("paused", 0)
        totals["liveRuns"] += row["liveRuns"]
        totals["schedulerActiveAgents"] += row["schedulerActiveAgents"]

    plugins = None
    plugin_tools = None
    if include_plugins:
        try:
            plugins = client.get("/plugins")
            plugin_tools = client.get("/plugins/tools")
        except Exception as exc:
            plugins = [{"error": str(exc)}]
            plugin_tools = []

    return {
        "generatedAt": iso_now(),
        "baseUrl": client.base_url.rstrip("/"),
        "health": health,
        "totals": totals,
        "companies": company_rows,
        "schedulerHeartbeatsSummary": summarize_heartbeats(heartbeats),
        "plugins": summarize_plugins(plugins) if plugins is not None else None,
        "pluginTools": [t.get("name") for t in plugin_tools or []],
        "diagnosis": build_diagnosis(totals, company_rows, heartbeats),
    }


def summarize_routine(r: Dict[str, Any]) -> Dict[str, Any]:
    last_run = r.get("lastRun") or {}
    return {
        "id": r.get("id"),
        "title": r.get("title"),
        "status": r.get("status"),
        "projectId": r.get("projectId"),
        "assigneeAgentId": r.get("assigneeAgentId"),
        "lastTriggeredAt": r.get("lastTriggeredAt"),
        "lastRunStatus": last_run.get("status"),
        "lastRunIssue": (last_run.get("linkedIssue") or {}).get("identifier"),
    }


def summarize_live_run(r: Dict[str, Any]) -> Dict[str, Any]:
    return {k: r.get(k) for k in ["id", "status", "agentName", "issueIdentifier", "startedAt", "updatedAt"] if k in r}


def summarize_plugins(plugins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"pluginKey": p.get("pluginKey"), "status": p.get("status"), "packageName": p.get("packageName"), "version": p.get("version")} for p in plugins]


def summarize_heartbeats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if rows and "error" in rows[0]:
        return {"error": rows[0]["error"]}
    return {
        "total": len(rows),
        "status": status_bucket(rows),
        "heartbeatEnabled": sum(1 for r in rows if r.get("heartbeatEnabled")),
        "schedulerActive": sum(1 for r in rows if r.get("schedulerActive")),
        "adapters": status_bucket(rows, "adapterType"),
    }


def find_duplicates(routines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in routines:
        key = normalize_title(str(r.get("title") or ""))
        if key:
            grouped[key].append(r)
    out = []
    for key, items in grouped.items():
        if len(items) > 1:
            out.append({"normalizedTitle": key, "count": len(items), "routines": [summarize_routine(r) for r in items]})
    return sorted(out, key=lambda x: x["count"], reverse=True)


def infer_node_kind(node: Dict[str, Any]) -> str:
    for key in ["kind", "type", "nodeType"]:
        value = node.get(key)
        if value:
            return str(value)
    node_id = str(node.get("id") or "")
    if ":" in node_id:
        return node_id.split(":", 1)[0]
    return "unknown"


def summarize_issue_workflow(identifier: str, workflow: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    nodes = workflow.get("nodes") if isinstance(workflow, dict) else None
    edges = workflow.get("edges") if isinstance(workflow, dict) else None
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []
    serialized = json.dumps(workflow, ensure_ascii=False, sort_keys=True)
    unsafe_raw_fields = []
    for field in ["message", "payload", "data"]:
        if f'"{field}"' in serialized:
            unsafe_raw_fields.append(field)
    node_kinds = status_bucket(({"kind": infer_node_kind(n)} for n in nodes), "kind") if nodes else {}
    node_status = status_bucket(nodes, "status") if nodes else {}
    return {
        "identifier": identifier,
        "baseUrl": base_url.rstrip("/"),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodeKinds": node_kinds,
        "nodeStatus": node_status,
        "hasDag": bool(nodes and edges),
        "usesMetadata": '"metadata"' in serialized,
        "unsafeRawFieldsDetected": unsafe_raw_fields,
        "uiUrl": f"{base_url.rstrip('/')}/{identifier.split('-', 1)[0]}/issues/{identifier}" if "-" in identifier else None,
        "sampleNodes": [{k: ({**n, "kind": infer_node_kind(n)}).get(k) for k in ["id", "kind", "status", "title"] if ({**n, "kind": infer_node_kind(n)}).get(k) is not None} for n in nodes[:8]],
        "sampleEdges": [{k: e.get(k) for k in ["id", "source", "target", "label"] if k in e} for e in edges[:8]],
        "diagnosis": build_issue_workflow_diagnosis(nodes, edges, unsafe_raw_fields),
    }


def build_issue_workflow_diagnosis(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], unsafe_raw_fields: List[str]) -> List[str]:
    notes = []
    if not nodes:
        notes.append("No workflow nodes returned; Live Workflow DAG will appear empty for this issue.")
    if nodes and not edges:
        notes.append("Workflow nodes returned without edges; DAG may render as disconnected cards.")
    if unsafe_raw_fields:
        notes.append("Raw workflow fields detected in serialized response: " + ", ".join(unsafe_raw_fields) + ". Verify API sanitization before release.")
    if nodes and edges and not unsafe_raw_fields:
        notes.append("Issue workflow DAG API is available and appears sanitized for UI rendering.")
    return notes


def build_diagnosis(totals: Dict[str, Any], company_rows: List[Dict[str, Any]], heartbeats: List[Dict[str, Any]]) -> List[str]:
    notes = []
    if totals["liveRuns"] == 0:
        notes.append("No live runs are currently active; UI/API may be up while workflows are idle.")
    if totals["activeRoutines"] == 0:
        notes.append("No active routines found; scheduled routine workflows will not run until resumed or created.")
    if totals["schedulerActiveAgents"] == 0:
        notes.append("No scheduler-active heartbeat agents found; autonomous agent heartbeat workflows appear disabled.")
    duplicate_count = sum(len(c.get("duplicateRoutineGroups", [])) for c in company_rows)
    if duplicate_count:
        notes.append(f"Potential duplicate routine title groups detected: {duplicate_count}.")
    if not notes:
        notes.append("Workflow control surface is active: live/scheduler/routine data is available.")
    return notes


def print_output(data: Any, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if isinstance(data, dict) and "totals" in data:
        print(f"Paperclip Workflow Control Snapshot — {data['baseUrl']}")
        print(f"Generated: {data['generatedAt']}")
        print(f"Health: {json.dumps(data.get('health'), ensure_ascii=False)}")
        print(f"Totals: {json.dumps(data['totals'], ensure_ascii=False, sort_keys=True)}")
        print("Diagnosis:")
        for note in data.get("diagnosis", []):
            print(f"- {note}")
        print("Companies:")
        for c in data.get("companies", []):
            print(f"- {c['name']} ({c.get('issuePrefix')}): routines={c['routines']} status={c['routineStatus']} liveRuns={c['liveRuns']} schedulerActive={c['schedulerActiveAgents']}/{c['schedulerAgents']}")
        if data.get("plugins") is not None:
            print(f"Plugins: {json.dumps(data['plugins'], ensure_ascii=False)}")
            print(f"Plugin tools: {', '.join(data.get('pluginTools') or []) or 'none'}")
        return
    if isinstance(data, dict) and "nodeCount" in data and "edgeCount" in data:
        print(f"Paperclip Issue Workflow DAG — {data['identifier']}")
        print(f"Base URL: {data['baseUrl']}")
        if data.get("uiUrl"):
            print(f"UI URL: {data['uiUrl']}")
        print(f"DAG: nodes={data['nodeCount']} edges={data['edgeCount']} hasDag={data['hasDag']} usesMetadata={data['usesMetadata']}")
        print(f"Node kinds: {json.dumps(data.get('nodeKinds', {}), ensure_ascii=False, sort_keys=True)}")
        print(f"Node status: {json.dumps(data.get('nodeStatus', {}), ensure_ascii=False, sort_keys=True)}")
        if data.get("unsafeRawFieldsDetected"):
            print(f"Unsafe raw fields detected: {', '.join(data['unsafeRawFieldsDetected'])}")
        print("Diagnosis:")
        for note in data.get("diagnosis", []):
            print(f"- {note}")
        return
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def require_apply(args: argparse.Namespace, action: str, payload: Dict[str, Any]) -> bool:
    preview = {"action": action, "target": getattr(args, "id", None), "payload": payload, "apply": bool(args.apply)}
    if not args.apply:
        print_output({"dryRun": True, **preview, "message": "No mutation sent. Re-run with --apply --confirm APPLY to execute."}, args.format)
        return False
    if args.confirm != "APPLY":
        raise PaperclipError("Mutation blocked: --apply requires --confirm APPLY")
    return True


def command_status(args: argparse.Namespace) -> None:
    client = make_client(args)
    data = collect_snapshot(client, args.company, include_plugins=not args.no_plugins)
    print_output(data, args.format)


def command_issue_workflow(args: argparse.Namespace) -> None:
    client = make_client(args)
    identifier = args.identifier.strip()
    workflow = client.get(f"/issues/{urllib.parse.quote(identifier)}/workflow")
    print_output(summarize_issue_workflow(identifier, workflow, client.base_url), args.format)


def command_pause(args: argparse.Namespace) -> None:
    payload = {"status": "paused"}
    if not require_apply(args, "pause-routine", payload):
        return
    result = make_client(args).patch(f"/routines/{urllib.parse.quote(args.id)}", payload)
    print_output({"applied": True, "routine": summarize_routine(result)}, args.format)


def command_resume(args: argparse.Namespace) -> None:
    payload = {"status": "active"}
    if not require_apply(args, "resume-routine", payload):
        return
    result = make_client(args).patch(f"/routines/{urllib.parse.quote(args.id)}", payload)
    print_output({"applied": True, "routine": summarize_routine(result)}, args.format)


def command_run(args: argparse.Namespace) -> None:
    payload: Dict[str, Any] = {}
    if args.variables_json:
        payload["variables"] = json.loads(args.variables_json)
    if not require_apply(args, "run-routine", payload):
        return
    result = make_client(args).post(f"/routines/{urllib.parse.quote(args.id)}/run", payload)
    print_output({"applied": True, "run": result}, args.format)


def command_update_trigger(args: argparse.Namespace) -> None:
    payload: Dict[str, Any] = {}
    if args.label is not None:
        payload["label"] = args.label
    if args.cron is not None:
        payload["cronExpression"] = args.cron
    if args.timezone is not None:
        payload["timezone"] = args.timezone
    if args.enabled is not None:
        payload["enabled"] = args.enabled
    if not payload:
        raise PaperclipError("No trigger fields provided. Use --cron, --label, --timezone, or --enabled.")
    if not require_apply(args, "update-routine-trigger", payload):
        return
    result = make_client(args).patch(f"/routine-triggers/{urllib.parse.quote(args.id)}", payload)
    print_output({"applied": True, "trigger": result}, args.format)


def make_client(args: argparse.Namespace) -> Client:
    base_url = args.base_url or os.environ.get("PAPERCLIP_BASE_URL") or os.environ.get("PAPERCLIP_WEB_URL") or DEFAULT_BASE_URL
    token = args.token or os.environ.get("PAPERCLIP_API_TOKEN")
    return Client(base_url=base_url, token=token, timeout=args.timeout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paperclip workflow diagnostics and approval-gated control")
    parser.add_argument("--base-url", default=None, help=f"Paperclip base URL (default: env or {DEFAULT_BASE_URL})")
    parser.add_argument("--token", default=None, help="Paperclip API token if required; otherwise uses PAPERCLIP_API_TOKEN")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Read-only workflow/scheduler/routine diagnostic snapshot")
    status.add_argument("--company", default=None, help="Company name, issue prefix, or id")
    status.add_argument("--no-plugins", action="store_true")
    status.set_defaults(func=command_status)

    issue_workflow = sub.add_parser("issue-workflow", help="Read-only Issue Detail Live Workflow DAG diagnostic")
    issue_workflow.add_argument("identifier", help="Issue identifier, e.g. WORK-2371")
    issue_workflow.set_defaults(func=command_issue_workflow)

    for name, func, help_text in [
        ("pause-routine", command_pause, "Pause a routine; dry-run unless --apply --confirm APPLY"),
        ("resume-routine", command_resume, "Resume a routine; dry-run unless --apply --confirm APPLY"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("id", help="Routine id")
        p.add_argument("--apply", action="store_true")
        p.add_argument("--confirm", default=None)
        p.set_defaults(func=func)

    run = sub.add_parser("run-routine", help="Manually run a routine; dry-run unless --apply --confirm APPLY")
    run.add_argument("id", help="Routine id")
    run.add_argument("--variables-json", default=None)
    run.add_argument("--apply", action="store_true")
    run.add_argument("--confirm", default=None)
    run.set_defaults(func=command_run)

    trig = sub.add_parser("update-trigger", help="Update a routine trigger; dry-run unless --apply --confirm APPLY")
    trig.add_argument("id", help="Routine trigger id")
    trig.add_argument("--cron", default=None)
    trig.add_argument("--label", default=None)
    trig.add_argument("--timezone", default=None)
    trig.add_argument("--enabled", choices=["true", "false"], default=None)
    trig.add_argument("--apply", action="store_true")
    trig.add_argument("--confirm", default=None)
    trig.set_defaults(func=command_update_trigger)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "enabled", None) is not None:
        args.enabled = args.enabled == "true"
    try:
        args.func(args)
        return 0
    except PaperclipError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
