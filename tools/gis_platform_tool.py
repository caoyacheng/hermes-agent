"""
GIS Platform tools for Hermes agent (LLM-callable).

This module follows the same pattern as the Home Assistant tool example:
- Uses env vars for configuration
- Registers multiple tools with schemas
- Returns compact JSON results suitable for LLM context

Config (env vars):
- GIS_API_URL: Base URL for the GIS backend (default: http://localhost:8080)
- GIS_API_TOKEN: Bearer JWT for calling the GIS backend (required for protected endpoints)
- GIS_TOOLS_ALLOW_WRITE: When "true", enable write tools (create/update/delete/ack/resolve)

Security notes:
- Write operations are disabled by default.
- This tool layer validates IDs/inputs and restricts method/path construction.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_GIS_API_URL: str = ""
_GIS_API_TOKEN: str = ""


def _get_config() -> Tuple[str, str]:
    """Return (base_url, token) from env vars at call time."""
    base = (_GIS_API_URL or os.getenv("GIS_API_URL", "http://localhost:8080")).rstrip("/")
    token = _GIS_API_TOKEN or os.getenv("GIS_API_TOKEN", "")
    return base, token


def _allow_write() -> bool:
    return os.getenv("GIS_TOOLS_ALLOW_WRITE", "").lower() == "true"


# Conservative ID format (matches current demo ids like CRD-001 / STA-C002 / station ids)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_]{0,63}$")
_PIPE_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{0,32}$")
_STATUS_RE = re.compile(r"^(all|normal|warning|repair|online|offline|alarm)$")


def _headers(token: str) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _http_json(
    method: str,
    path: str,
    query: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout_s: int = 15,
) -> Any:
    base, token = _get_config()
    if not path.startswith("/"):
        raise ValueError("path must start with '/'")

    url = f"{base}{path}"
    if query:
        qs = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None}, doseq=True)
        if qs:
            url = f"{url}?{qs}"

    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url=url, method=method.upper(), headers=_headers(token), data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            if not raw:
                return None
            ct = resp.headers.get("Content-Type", "")
            if "application/json" in ct:
                return json.loads(raw.decode("utf-8"))
            return raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        # Include status + a short body snippet if present for debugging.
        body = b""
        try:
            body = e.read() or b""
        except Exception:
            body = b""
        snippet = ""
        if body:
            try:
                snippet = body.decode("utf-8", errors="replace")[:800]
            except Exception:
                snippet = repr(body[:200])
        msg = f"HTTP {getattr(e, 'code', 'error')} {getattr(e, 'reason', '')}".strip()
        if snippet:
            msg = f"{msg} — {snippet}"
        logger.error("GIS tool request failed: %s %s: %s", method, url, msg)
        raise RuntimeError(msg) from e
    except Exception as e:
        logger.error("GIS tool request failed: %s %s: %s", method, url, e)
        raise


def _check_available() -> bool:
    """Tools are available when token is configured (or backend allows anonymous)."""
    _, token = _get_config()
    return bool(token) or os.getenv("GIS_ALLOW_ANON", "").lower() == "true"


def _require_id(name: str, v: str) -> Optional[str]:
    if not v:
        return f"Missing required parameter: {name}"
    if not _ID_RE.match(v):
        return f"Invalid {name} format: {v!r}"
    return None


def _compact_feature_collection(data: Any, limit: int = 50) -> Dict[str, Any]:
    """Compact GeoJSON FeatureCollection-like payload to reduce context."""
    if not isinstance(data, dict):
        return {"raw": data}
    features = data.get("features")
    if not isinstance(features, list):
        return {"raw": data}
    items = []
    for f in features[: max(0, min(limit, len(features)))]:
        props = (f or {}).get("properties", {}) if isinstance(f, dict) else {}
        items.append(
            {
                "id": props.get("id"),
                "name": props.get("name"),
                "status": props.get("status"),
                "type": props.get("pipeType") or props.get("stationType"),
            }
        )
    return {"count": len(features), "items": items}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def _handle_auth_me(args: dict, **kw) -> str:
    try:
        data = _http_json("GET", "/api/auth/me", timeout_s=10)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get current user: {e}")


def _handle_list_pipelines(args: dict, **kw) -> str:
    pipe_type = args.get("type")
    status = args.get("status")
    if pipe_type and not _PIPE_TYPE_RE.match(pipe_type):
        return tool_error(f"Invalid type: {pipe_type!r}")
    if status and not _STATUS_RE.match(status):
        return tool_error(f"Invalid status: {status!r}")
    try:
        data = _http_json("GET", "/api/pipelines", query={"type": pipe_type, "status": status})
        return json.dumps({"result": _compact_feature_collection(data)})
    except Exception as e:
        return tool_error(f"Failed to list pipelines: {e}")


def _handle_get_pipeline(args: dict, **kw) -> str:
    pid = args.get("id", "")
    err = _require_id("id", pid)
    if err:
        return tool_error(err)
    try:
        data = _http_json("GET", f"/api/pipelines/{urllib.parse.quote(pid)}")
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get pipeline {pid}: {e}")


def _handle_list_pipelines_bbox(args: dict, **kw) -> str:
    try:
        min_lng = float(args.get("minLng"))
        min_lat = float(args.get("minLat"))
        max_lng = float(args.get("maxLng"))
        max_lat = float(args.get("maxLat"))
    except Exception:
        return tool_error("Missing/invalid bbox params: minLng, minLat, maxLng, maxLat must be numbers")
    try:
        data = _http_json(
            "GET",
            "/api/pipelines/bbox",
            query={"minLng": min_lng, "minLat": min_lat, "maxLng": max_lng, "maxLat": max_lat},
        )
        return json.dumps({"result": _compact_feature_collection(data)})
    except Exception as e:
        return tool_error(f"Failed to list pipelines by bbox: {e}")


def _handle_create_pipeline(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    body = args.get("pipeline")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: pipeline (object)")
    try:
        data = _http_json("POST", "/api/pipelines", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to create pipeline: {e}")


def _handle_update_pipeline(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    pid = args.get("id", "")
    err = _require_id("id", pid)
    if err:
        return tool_error(err)
    body = args.get("pipeline")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: pipeline (object)")
    try:
        data = _http_json("PUT", f"/api/pipelines/{urllib.parse.quote(pid)}", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to update pipeline {pid}: {e}")


def _handle_delete_pipeline(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    pid = args.get("id", "")
    err = _require_id("id", pid)
    if err:
        return tool_error(err)
    try:
        _http_json("DELETE", f"/api/pipelines/{urllib.parse.quote(pid)}", timeout_s=25)
        return json.dumps({"result": {"success": True, "deleted": pid}})
    except Exception as e:
        return tool_error(f"Failed to delete pipeline {pid}: {e}")


def _handle_list_stations(args: dict, **kw) -> str:
    st_type = args.get("type")
    status = args.get("status")
    if st_type and not _PIPE_TYPE_RE.match(st_type):
        return tool_error(f"Invalid type: {st_type!r}")
    if status and not _STATUS_RE.match(status):
        return tool_error(f"Invalid status: {status!r}")
    try:
        data = _http_json("GET", "/api/stations", query={"type": st_type, "status": status})
        return json.dumps({"result": _compact_feature_collection(data)})
    except Exception as e:
        return tool_error(f"Failed to list stations: {e}")


def _handle_get_station(args: dict, **kw) -> str:
    sid = args.get("id", "")
    err = _require_id("id", sid)
    if err:
        return tool_error(err)
    try:
        data = _http_json("GET", f"/api/stations/{urllib.parse.quote(sid)}")
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get station {sid}: {e}")


def _handle_list_stations_by_pipe(args: dict, **kw) -> str:
    pid = args.get("pipeId", "")
    err = _require_id("pipeId", pid)
    if err:
        return tool_error(err)
    try:
        data = _http_json("GET", f"/api/stations/bindPipe/{urllib.parse.quote(pid)}")
        return json.dumps({"result": _compact_feature_collection(data)})
    except Exception as e:
        return tool_error(f"Failed to list stations for pipe {pid}: {e}")


def _handle_create_station(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    body = args.get("station")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: station (object)")
    try:
        data = _http_json("POST", "/api/stations", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to create station: {e}")


def _handle_update_station(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    sid = args.get("id", "")
    err = _require_id("id", sid)
    if err:
        return tool_error(err)
    body = args.get("station")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: station (object)")
    try:
        data = _http_json("PUT", f"/api/stations/{urllib.parse.quote(sid)}", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to update station {sid}: {e}")


def _handle_delete_station(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    sid = args.get("id", "")
    err = _require_id("id", sid)
    if err:
        return tool_error(err)
    try:
        _http_json("DELETE", f"/api/stations/{urllib.parse.quote(sid)}", timeout_s=25)
        return json.dumps({"result": {"success": True, "deleted": sid}})
    except Exception as e:
        return tool_error(f"Failed to delete station {sid}: {e}")


def _handle_stats_overview(args: dict, **kw) -> str:
    try:
        data = _http_json("GET", "/api/stats/overview")
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get stats overview: {e}")


def _handle_list_alarms(args: dict, **kw) -> str:
    resolved = args.get("resolved")
    station_id = args.get("stationId")
    if station_id:
        err = _require_id("stationId", station_id)
        if err:
            return tool_error(err)
    if resolved is not None and not isinstance(resolved, bool):
        return tool_error("resolved must be boolean if provided")
    try:
        data = _http_json("GET", "/api/alarms", query={"resolved": resolved, "stationId": station_id})
        items = []
        if isinstance(data, list):
            for a in data[:100]:
                if isinstance(a, dict):
                    items.append(
                        {
                            "id": a.get("id"),
                            "stationId": a.get("stationId"),
                            "metric": a.get("metric"),
                            "level": a.get("level"),
                            "resolved": a.get("resolved"),
                            "createdAt": a.get("createdAt"),
                        }
                    )
        return json.dumps({"result": {"count": len(data) if isinstance(data, list) else None, "items": items}})
    except Exception as e:
        return tool_error(f"Failed to list alarms: {e}")


def _handle_get_alarm(args: dict, **kw) -> str:
    alarm_id = args.get("id")
    if alarm_id is None:
        return tool_error("Missing required parameter: id")
    try:
        int_id = int(alarm_id)
    except Exception:
        return tool_error("id must be an integer")
    try:
        data = _http_json("GET", f"/api/alarms/{int_id}")
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get alarm {alarm_id}: {e}")


def _handle_ack_alarm(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    alarm_id = args.get("id")
    if alarm_id is None:
        return tool_error("Missing required parameter: id")
    try:
        int_id = int(alarm_id)
    except Exception:
        return tool_error("id must be an integer")
    try:
        data = _http_json("POST", f"/api/alarms/{int_id}/acknowledge", timeout_s=20)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to acknowledge alarm {alarm_id}: {e}")


def _handle_resolve_alarm(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    alarm_id = args.get("id")
    note = args.get("resolutionNote")
    if alarm_id is None:
        return tool_error("Missing required parameter: id")
    try:
        int_id = int(alarm_id)
    except Exception:
        return tool_error("id must be an integer")
    body = {"resolutionNote": note} if note else None
    try:
        data = _http_json("PUT", f"/api/alarms/{int_id}/resolve", body=body, timeout_s=20)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to resolve alarm {alarm_id}: {e}")


def _handle_list_alarm_rules(args: dict, **kw) -> str:
    try:
        data = _http_json("GET", "/api/alarm-rules")
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to list alarm rules: {e}")


def _handle_create_alarm_rule(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    dto = args.get("rule")
    if not isinstance(dto, dict):
        return tool_error("Missing required parameter: rule (object)")
    try:
        data = _http_json("POST", "/api/alarm-rules", body=dto, timeout_s=20)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to create alarm rule: {e}")


def _handle_update_alarm_rule(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    rid = args.get("id")
    dto = args.get("rule")
    if rid is None:
        return tool_error("Missing required parameter: id")
    if not isinstance(dto, dict):
        return tool_error("Missing required parameter: rule (object)")
    try:
        int_id = int(rid)
    except Exception:
        return tool_error("id must be an integer")
    try:
        data = _http_json("PUT", f"/api/alarm-rules/{int_id}", body=dto, timeout_s=20)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to update alarm rule {rid}: {e}")


def _handle_delete_alarm_rule(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    rid = args.get("id")
    if rid is None:
        return tool_error("Missing required parameter: id")
    try:
        int_id = int(rid)
    except Exception:
        return tool_error("id must be an integer")
    try:
        _http_json("DELETE", f"/api/alarm-rules/{int_id}", timeout_s=20)
        return json.dumps({"result": {"success": True, "deleted": int_id}})
    except Exception as e:
        return tool_error(f"Failed to delete alarm rule {rid}: {e}")


def _handle_list_audit_logs(args: dict, **kw) -> str:
    query = {
        "username": args.get("username"),
        "action": args.get("action"),
        "target": args.get("target"),
        "startDate": args.get("startDate"),
        "endDate": args.get("endDate"),
        "page": args.get("page", 0),
        "size": min(int(args.get("size", 20)), 100),
    }
    try:
        data = _http_json("GET", "/api/audit-logs", query=query, timeout_s=15)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to list audit logs: {e}")


def _handle_audit_stats(args: dict, **kw) -> str:
    try:
        data = _http_json("GET", "/api/audit-logs/stats", timeout_s=15)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get audit stats: {e}")


def _handle_list_inspection_plans(args: dict, **kw) -> str:
    try:
        data = _http_json(
            "GET",
            "/api/inspection-plans",
            query={"status": args.get("status"), "pipelineId": args.get("pipelineId")},
            timeout_s=20,
        )
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to list inspection plans: {e}")


def _handle_get_inspection_plan(args: dict, **kw) -> str:
    pid = args.get("id", "")
    err = _require_id("id", pid)
    if err:
        return tool_error(err)
    try:
        data = _http_json("GET", f"/api/inspection-plans/{urllib.parse.quote(pid)}", timeout_s=15)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get inspection plan {pid}: {e}")


def _handle_create_inspection_plan(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    body = args.get("plan")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: plan (object)")
    try:
        data = _http_json("POST", "/api/inspection-plans", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to create inspection plan: {e}")


def _handle_update_inspection_plan(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    pid = args.get("id", "")
    err = _require_id("id", pid)
    if err:
        return tool_error(err)
    body = args.get("plan")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: plan (object)")
    try:
        data = _http_json("PUT", f"/api/inspection-plans/{urllib.parse.quote(pid)}", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to update inspection plan {pid}: {e}")


def _handle_delete_inspection_plan(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    pid = args.get("id", "")
    err = _require_id("id", pid)
    if err:
        return tool_error(err)
    try:
        _http_json("DELETE", f"/api/inspection-plans/{urllib.parse.quote(pid)}", timeout_s=25)
        return json.dumps({"result": {"success": True, "deleted": pid}})
    except Exception as e:
        return tool_error(f"Failed to delete inspection plan {pid}: {e}")


def _handle_list_inspection_records(args: dict, **kw) -> str:
    try:
        data = _http_json(
            "GET",
            "/api/inspection-records",
            query={"planId": args.get("planId"), "status": args.get("status")},
            timeout_s=20,
        )
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to list inspection records: {e}")


def _handle_get_inspection_record(args: dict, **kw) -> str:
    rid = args.get("id")
    if rid is None:
        return tool_error("Missing required parameter: id")
    try:
        int_id = int(rid)
    except Exception:
        return tool_error("id must be an integer")
    try:
        data = _http_json("GET", f"/api/inspection-records/{int_id}", timeout_s=15)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get inspection record {rid}: {e}")


def _handle_create_inspection_record(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    body = args.get("record")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: record (object)")
    try:
        data = _http_json("POST", "/api/inspection-records", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to create inspection record: {e}")


def _handle_update_inspection_record(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    rid = args.get("id")
    body = args.get("record")
    if rid is None:
        return tool_error("Missing required parameter: id")
    if not isinstance(body, dict):
        return tool_error("Missing required parameter: record (object)")
    try:
        int_id = int(rid)
    except Exception:
        return tool_error("id must be an integer")
    try:
        data = _http_json("PUT", f"/api/inspection-records/{int_id}", body=body, timeout_s=25)
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to update inspection record {rid}: {e}")


def _handle_delete_inspection_record(args: dict, **kw) -> str:
    if not _allow_write():
        return tool_error("Write tools are disabled. Set GIS_TOOLS_ALLOW_WRITE=true to enable.")
    rid = args.get("id")
    if rid is None:
        return tool_error("Missing required parameter: id")
    try:
        int_id = int(rid)
    except Exception:
        return tool_error("id must be an integer")
    try:
        _http_json("DELETE", f"/api/inspection-records/{int_id}", timeout_s=25)
        return json.dumps({"result": {"success": True, "deleted": int_id}})
    except Exception as e:
        return tool_error(f"Failed to delete inspection record {rid}: {e}")


def _handle_topology_connections(args: dict, **kw) -> str:
    pid = args.get("pipeId", "")
    err = _require_id("pipeId", pid)
    if err:
        return tool_error(err)
    try:
        data = _http_json("GET", f"/api/topology/connections/{urllib.parse.quote(pid)}")
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to get connections for {pid}: {e}")


def _handle_topology_trace(args: dict, **kw) -> str:
    start = args.get("startPipeId", "")
    direction = args.get("direction", "both")
    err = _require_id("startPipeId", start)
    if err:
        return tool_error(err)
    if direction not in ("both", "upstream", "downstream"):
        return tool_error("direction must be one of: both, upstream, downstream")
    try:
        data = _http_json("GET", "/api/topology/trace", query={"startPipeId": start, "direction": direction})
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to trace topology from {start}: {e}")


def _handle_topology_shutoff(args: dict, **kw) -> str:
    valve = args.get("valveStationId", "")
    err = _require_id("valveStationId", valve)
    if err:
        return tool_error(err)
    try:
        data = _http_json("GET", "/api/topology/shutoff", query={"valveStationId": valve})
        return json.dumps({"result": data})
    except Exception as e:
        return tool_error(f"Failed to simulate shutoff for {valve}: {e}")


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

GIS_AUTH_ME_SCHEMA = {
    "name": "gis_auth_me",
    "description": "Get current user info from token (GET /api/auth/me).",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

GIS_LIST_PIPELINES_SCHEMA = {
    "name": "gis_list_pipelines",
    "description": "List pipelines (GeoJSON FeatureCollection). Optional filter by type/status.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "description": "Pipeline type filter, e.g. crude/product/gas/condensate."},
            "status": {"type": "string", "description": "Pipeline status filter, e.g. normal/warning/repair."},
        },
        "required": [],
    },
}

GIS_GET_PIPELINE_SCHEMA = {
    "name": "gis_get_pipeline",
    "description": "Get a single pipeline by ID (returns a GeoJSON Feature-like object).",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}

GIS_LIST_PIPELINES_BBOX_SCHEMA = {
    "name": "gis_list_pipelines_bbox",
    "description": "List pipelines within a bounding box (minLng,minLat,maxLng,maxLat).",
    "parameters": {
        "type": "object",
        "properties": {
            "minLng": {"type": "number"},
            "minLat": {"type": "number"},
            "maxLng": {"type": "number"},
            "maxLat": {"type": "number"},
        },
        "required": ["minLng", "minLat", "maxLng", "maxLat"],
    },
}

GIS_CREATE_PIPELINE_SCHEMA = {
    "name": "gis_create_pipeline",
    "description": "Create a pipeline (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"pipeline": {"type": "object"}}, "required": ["pipeline"]},
}

GIS_UPDATE_PIPELINE_SCHEMA = {
    "name": "gis_update_pipeline",
    "description": "Update a pipeline by ID (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "pipeline": {"type": "object"}},
        "required": ["id", "pipeline"],
    },
}

GIS_DELETE_PIPELINE_SCHEMA = {
    "name": "gis_delete_pipeline",
    "description": "Delete a pipeline by ID (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}

GIS_LIST_STATIONS_SCHEMA = {
    "name": "gis_list_stations",
    "description": "List stations (GeoJSON FeatureCollection). Optional filter by type/status.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "description": "Station type filter."},
            "status": {"type": "string", "description": "Station status filter: online/offline/alarm."},
        },
        "required": [],
    },
}

GIS_GET_STATION_SCHEMA = {
    "name": "gis_get_station",
    "description": "Get a single station by ID.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}

GIS_LIST_STATIONS_BY_PIPE_SCHEMA = {
    "name": "gis_list_stations_by_pipe",
    "description": "List stations bound to a pipeline ID.",
    "parameters": {"type": "object", "properties": {"pipeId": {"type": "string"}}, "required": ["pipeId"]},
}

GIS_CREATE_STATION_SCHEMA = {
    "name": "gis_create_station",
    "description": "Create a station (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"station": {"type": "object"}}, "required": ["station"]},
}

GIS_UPDATE_STATION_SCHEMA = {
    "name": "gis_update_station",
    "description": "Update a station by ID (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "station": {"type": "object"}},
        "required": ["id", "station"],
    },
}

GIS_DELETE_STATION_SCHEMA = {
    "name": "gis_delete_station",
    "description": "Delete a station by ID (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}

GIS_STATS_OVERVIEW_SCHEMA = {
    "name": "gis_stats_overview",
    "description": "Get platform overview stats (/api/stats/overview).",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

GIS_LIST_ALARMS_SCHEMA = {
    "name": "gis_list_alarms",
    "description": "List alarms with optional filters resolved/stationId.",
    "parameters": {
        "type": "object",
        "properties": {
            "resolved": {"type": "boolean", "description": "Filter by resolved flag."},
            "stationId": {"type": "string", "description": "Filter by station ID."},
        },
        "required": [],
    },
}

GIS_GET_ALARM_SCHEMA = {
    "name": "gis_get_alarm",
    "description": "Get an alarm by integer ID.",
    "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
}

GIS_ACK_ALARM_SCHEMA = {
    "name": "gis_ack_alarm",
    "description": "Acknowledge an alarm (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
}

GIS_RESOLVE_ALARM_SCHEMA = {
    "name": "gis_resolve_alarm",
    "description": "Resolve an alarm with optional resolutionNote (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "resolutionNote": {"type": "string"}},
        "required": ["id"],
    },
}

GIS_LIST_ALARM_RULES_SCHEMA = {
    "name": "gis_list_alarm_rules",
    "description": "List alarm rules.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

GIS_CREATE_ALARM_RULE_SCHEMA = {
    "name": "gis_create_alarm_rule",
    "description": "Create an alarm rule (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"rule": {"type": "object"}}, "required": ["rule"]},
}

GIS_UPDATE_ALARM_RULE_SCHEMA = {
    "name": "gis_update_alarm_rule",
    "description": "Update an alarm rule by integer ID (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "rule": {"type": "object"}},
        "required": ["id", "rule"],
    },
}

GIS_DELETE_ALARM_RULE_SCHEMA = {
    "name": "gis_delete_alarm_rule",
    "description": "Delete an alarm rule by integer ID (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
}

GIS_LIST_AUDIT_LOGS_SCHEMA = {
    "name": "gis_list_audit_logs",
    "description": "List audit logs with filters (GET /api/audit-logs).",
    "parameters": {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "action": {"type": "string"},
            "target": {"type": "string"},
            "startDate": {"type": "string", "description": "YYYY-MM-DD"},
            "endDate": {"type": "string", "description": "YYYY-MM-DD"},
            "page": {"type": "integer", "description": "0-based"},
            "size": {"type": "integer", "description": "max 100"},
        },
        "required": [],
    },
}

GIS_AUDIT_STATS_SCHEMA = {
    "name": "gis_audit_stats",
    "description": "Get audit log statistics (GET /api/audit-logs/stats).",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

GIS_LIST_INSPECTION_PLANS_SCHEMA = {
    "name": "gis_list_inspection_plans",
    "description": "List inspection plans with optional filters status/pipelineId.",
    "parameters": {
        "type": "object",
        "properties": {"status": {"type": "string"}, "pipelineId": {"type": "string"}},
        "required": [],
    },
}

GIS_GET_INSPECTION_PLAN_SCHEMA = {
    "name": "gis_get_inspection_plan",
    "description": "Get an inspection plan by ID.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}

GIS_CREATE_INSPECTION_PLAN_SCHEMA = {
    "name": "gis_create_inspection_plan",
    "description": "Create an inspection plan (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"plan": {"type": "object"}}, "required": ["plan"]},
}

GIS_UPDATE_INSPECTION_PLAN_SCHEMA = {
    "name": "gis_update_inspection_plan",
    "description": "Update an inspection plan (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "plan": {"type": "object"}},
        "required": ["id", "plan"],
    },
}

GIS_DELETE_INSPECTION_PLAN_SCHEMA = {
    "name": "gis_delete_inspection_plan",
    "description": "Delete an inspection plan (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}

GIS_LIST_INSPECTION_RECORDS_SCHEMA = {
    "name": "gis_list_inspection_records",
    "description": "List inspection records with optional filters planId/status.",
    "parameters": {"type": "object", "properties": {"planId": {"type": "string"}, "status": {"type": "string"}}, "required": []},
}

GIS_GET_INSPECTION_RECORD_SCHEMA = {
    "name": "gis_get_inspection_record",
    "description": "Get an inspection record by integer ID.",
    "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
}

GIS_CREATE_INSPECTION_RECORD_SCHEMA = {
    "name": "gis_create_inspection_record",
    "description": "Create an inspection record (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"record": {"type": "object"}}, "required": ["record"]},
}

GIS_UPDATE_INSPECTION_RECORD_SCHEMA = {
    "name": "gis_update_inspection_record",
    "description": "Update an inspection record (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"id": {"type": "integer"}, "record": {"type": "object"}}, "required": ["id", "record"]},
}

GIS_DELETE_INSPECTION_RECORD_SCHEMA = {
    "name": "gis_delete_inspection_record",
    "description": "Delete an inspection record (write). Requires GIS_TOOLS_ALLOW_WRITE=true.",
    "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
}

GIS_TOPOLOGY_CONNECTIONS_SCHEMA = {
    "name": "gis_topology_connections",
    "description": "Get direct connections for a pipeline ID.",
    "parameters": {"type": "object", "properties": {"pipeId": {"type": "string"}}, "required": ["pipeId"]},
}

GIS_TOPOLOGY_TRACE_SCHEMA = {
    "name": "gis_topology_trace",
    "description": "Trace connectivity from a pipeline ID (direction: both/upstream/downstream).",
    "parameters": {
        "type": "object",
        "properties": {"startPipeId": {"type": "string"}, "direction": {"type": "string"}},
        "required": ["startPipeId"],
    },
}

GIS_TOPOLOGY_SHUTOFF_SCHEMA = {
    "name": "gis_topology_shutoff",
    "description": "Simulate valve shutoff (requires valve station ID).",
    "parameters": {"type": "object", "properties": {"valveStationId": {"type": "string"}}, "required": ["valveStationId"]},
}


try:
    from tools.registry import registry, tool_error  # type: ignore
except Exception:  # pragma: no cover
    class _NoopRegistry:
        def register(self, *args, **kwargs):  # noqa: ANN001
            return None

    def tool_error(message: str) -> str:  # type: ignore
        return json.dumps({"error": message}, ensure_ascii=False)

    registry = _NoopRegistry()  # type: ignore


registry.register(
    name="gis_auth_me",
    toolset="gis_platform",
    schema=GIS_AUTH_ME_SCHEMA,
    handler=_handle_auth_me,
    check_fn=_check_available,
    emoji="👤",
)

registry.register(
    name="gis_list_pipelines",
    toolset="gis_platform",
    schema=GIS_LIST_PIPELINES_SCHEMA,
    handler=_handle_list_pipelines,
    check_fn=_check_available,
    emoji="🗺️",
)

registry.register(
    name="gis_get_pipeline",
    toolset="gis_platform",
    schema=GIS_GET_PIPELINE_SCHEMA,
    handler=_handle_get_pipeline,
    check_fn=_check_available,
    emoji="🛢️",
)

registry.register(
    name="gis_list_pipelines_bbox",
    toolset="gis_platform",
    schema=GIS_LIST_PIPELINES_BBOX_SCHEMA,
    handler=_handle_list_pipelines_bbox,
    check_fn=_check_available,
    emoji="📦",
)

registry.register(
    name="gis_create_pipeline",
    toolset="gis_platform",
    schema=GIS_CREATE_PIPELINE_SCHEMA,
    handler=_handle_create_pipeline,
    check_fn=_check_available,
    emoji="➕",
)

registry.register(
    name="gis_update_pipeline",
    toolset="gis_platform",
    schema=GIS_UPDATE_PIPELINE_SCHEMA,
    handler=_handle_update_pipeline,
    check_fn=_check_available,
    emoji="✏️",
)

registry.register(
    name="gis_delete_pipeline",
    toolset="gis_platform",
    schema=GIS_DELETE_PIPELINE_SCHEMA,
    handler=_handle_delete_pipeline,
    check_fn=_check_available,
    emoji="🗑️",
)

registry.register(
    name="gis_list_stations",
    toolset="gis_platform",
    schema=GIS_LIST_STATIONS_SCHEMA,
    handler=_handle_list_stations,
    check_fn=_check_available,
    emoji="🏭",
)

registry.register(
    name="gis_get_station",
    toolset="gis_platform",
    schema=GIS_GET_STATION_SCHEMA,
    handler=_handle_get_station,
    check_fn=_check_available,
    emoji="🏭",
)

registry.register(
    name="gis_list_stations_by_pipe",
    toolset="gis_platform",
    schema=GIS_LIST_STATIONS_BY_PIPE_SCHEMA,
    handler=_handle_list_stations_by_pipe,
    check_fn=_check_available,
    emoji="🔗",
)

registry.register(
    name="gis_create_station",
    toolset="gis_platform",
    schema=GIS_CREATE_STATION_SCHEMA,
    handler=_handle_create_station,
    check_fn=_check_available,
    emoji="➕",
)

registry.register(
    name="gis_update_station",
    toolset="gis_platform",
    schema=GIS_UPDATE_STATION_SCHEMA,
    handler=_handle_update_station,
    check_fn=_check_available,
    emoji="✏️",
)

registry.register(
    name="gis_delete_station",
    toolset="gis_platform",
    schema=GIS_DELETE_STATION_SCHEMA,
    handler=_handle_delete_station,
    check_fn=_check_available,
    emoji="🗑️",
)

registry.register(
    name="gis_stats_overview",
    toolset="gis_platform",
    schema=GIS_STATS_OVERVIEW_SCHEMA,
    handler=_handle_stats_overview,
    check_fn=_check_available,
    emoji="📈",
)

registry.register(
    name="gis_list_alarms",
    toolset="gis_platform",
    schema=GIS_LIST_ALARMS_SCHEMA,
    handler=_handle_list_alarms,
    check_fn=_check_available,
    emoji="🚨",
)

registry.register(
    name="gis_get_alarm",
    toolset="gis_platform",
    schema=GIS_GET_ALARM_SCHEMA,
    handler=_handle_get_alarm,
    check_fn=_check_available,
    emoji="🚨",
)

registry.register(
    name="gis_ack_alarm",
    toolset="gis_platform",
    schema=GIS_ACK_ALARM_SCHEMA,
    handler=_handle_ack_alarm,
    check_fn=_check_available,
    emoji="✅",
)

registry.register(
    name="gis_resolve_alarm",
    toolset="gis_platform",
    schema=GIS_RESOLVE_ALARM_SCHEMA,
    handler=_handle_resolve_alarm,
    check_fn=_check_available,
    emoji="🧯",
)

registry.register(
    name="gis_list_alarm_rules",
    toolset="gis_platform",
    schema=GIS_LIST_ALARM_RULES_SCHEMA,
    handler=_handle_list_alarm_rules,
    check_fn=_check_available,
    emoji="📏",
)

registry.register(
    name="gis_create_alarm_rule",
    toolset="gis_platform",
    schema=GIS_CREATE_ALARM_RULE_SCHEMA,
    handler=_handle_create_alarm_rule,
    check_fn=_check_available,
    emoji="➕",
)

registry.register(
    name="gis_update_alarm_rule",
    toolset="gis_platform",
    schema=GIS_UPDATE_ALARM_RULE_SCHEMA,
    handler=_handle_update_alarm_rule,
    check_fn=_check_available,
    emoji="✏️",
)

registry.register(
    name="gis_delete_alarm_rule",
    toolset="gis_platform",
    schema=GIS_DELETE_ALARM_RULE_SCHEMA,
    handler=_handle_delete_alarm_rule,
    check_fn=_check_available,
    emoji="🗑️",
)

registry.register(
    name="gis_list_audit_logs",
    toolset="gis_platform",
    schema=GIS_LIST_AUDIT_LOGS_SCHEMA,
    handler=_handle_list_audit_logs,
    check_fn=_check_available,
    emoji="🧾",
)

registry.register(
    name="gis_audit_stats",
    toolset="gis_platform",
    schema=GIS_AUDIT_STATS_SCHEMA,
    handler=_handle_audit_stats,
    check_fn=_check_available,
    emoji="📊",
)

registry.register(
    name="gis_list_inspection_plans",
    toolset="gis_platform",
    schema=GIS_LIST_INSPECTION_PLANS_SCHEMA,
    handler=_handle_list_inspection_plans,
    check_fn=_check_available,
    emoji="🗓️",
)

registry.register(
    name="gis_get_inspection_plan",
    toolset="gis_platform",
    schema=GIS_GET_INSPECTION_PLAN_SCHEMA,
    handler=_handle_get_inspection_plan,
    check_fn=_check_available,
    emoji="🗓️",
)

registry.register(
    name="gis_create_inspection_plan",
    toolset="gis_platform",
    schema=GIS_CREATE_INSPECTION_PLAN_SCHEMA,
    handler=_handle_create_inspection_plan,
    check_fn=_check_available,
    emoji="➕",
)

registry.register(
    name="gis_update_inspection_plan",
    toolset="gis_platform",
    schema=GIS_UPDATE_INSPECTION_PLAN_SCHEMA,
    handler=_handle_update_inspection_plan,
    check_fn=_check_available,
    emoji="✏️",
)

registry.register(
    name="gis_delete_inspection_plan",
    toolset="gis_platform",
    schema=GIS_DELETE_INSPECTION_PLAN_SCHEMA,
    handler=_handle_delete_inspection_plan,
    check_fn=_check_available,
    emoji="🗑️",
)

registry.register(
    name="gis_list_inspection_records",
    toolset="gis_platform",
    schema=GIS_LIST_INSPECTION_RECORDS_SCHEMA,
    handler=_handle_list_inspection_records,
    check_fn=_check_available,
    emoji="📋",
)

registry.register(
    name="gis_get_inspection_record",
    toolset="gis_platform",
    schema=GIS_GET_INSPECTION_RECORD_SCHEMA,
    handler=_handle_get_inspection_record,
    check_fn=_check_available,
    emoji="📋",
)

registry.register(
    name="gis_create_inspection_record",
    toolset="gis_platform",
    schema=GIS_CREATE_INSPECTION_RECORD_SCHEMA,
    handler=_handle_create_inspection_record,
    check_fn=_check_available,
    emoji="➕",
)

registry.register(
    name="gis_update_inspection_record",
    toolset="gis_platform",
    schema=GIS_UPDATE_INSPECTION_RECORD_SCHEMA,
    handler=_handle_update_inspection_record,
    check_fn=_check_available,
    emoji="✏️",
)

registry.register(
    name="gis_delete_inspection_record",
    toolset="gis_platform",
    schema=GIS_DELETE_INSPECTION_RECORD_SCHEMA,
    handler=_handle_delete_inspection_record,
    check_fn=_check_available,
    emoji="🗑️",
)

registry.register(
    name="gis_topology_connections",
    toolset="gis_platform",
    schema=GIS_TOPOLOGY_CONNECTIONS_SCHEMA,
    handler=_handle_topology_connections,
    check_fn=_check_available,
    emoji="🧩",
)

registry.register(
    name="gis_topology_trace",
    toolset="gis_platform",
    schema=GIS_TOPOLOGY_TRACE_SCHEMA,
    handler=_handle_topology_trace,
    check_fn=_check_available,
    emoji="🧭",
)

registry.register(
    name="gis_topology_shutoff",
    toolset="gis_platform",
    schema=GIS_TOPOLOGY_SHUTOFF_SCHEMA,
    handler=_handle_topology_shutoff,
    check_fn=_check_available,
    emoji="🛑",
)

