"""Crimp serve — FastAPI commissioning web UI.

Runs on the Pi 4 (connected to hardware). Access from laptop via WiFi:
    http://pi4.local:8000
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from crimp.manifest import Manifest

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Wire colour → approximate CSS colour for the badge
_WIRE_CSS = {
    "red":    "#f44336",
    "black":  "#78909c",
    "blue":   "#42a5f5",
    "yellow": "#ffd54f",
    "white":  "#eeeeee",
    "orange": "#ff9800",
    "green":  "#66bb6a",
    "brown":  "#8d6e63",
    "purple": "#ab47bc",
    "grey":   "#90a4ae",
    "gray":   "#90a4ae",
    "pink":   "#f48fb1",
}

_PHASE_ORDER = [
    "Phase 1 — Power wiring",
    "Phase 2 — Sensors (I²C / UART / RC)",
    "Phase 3 — Relay board",
    "Phase 4 — PWM & control signals",
    "Phase 5 — Network & peripherals",
    "Phase 6 — AC mains / charging",
]


def _phase_name(order: int) -> str:
    from crimp.generators.assembly import _phase_name as _pn
    return _pn(order)


def _conn_ctx(manifest: Manifest, conn, step_num: int, status: str) -> dict[str, Any]:
    """Build template context dict for a single connection."""
    from_comp = manifest.components[conn.from_.component]
    to_comp = manifest.components[conn.to.component]
    color = conn.wire.color or ""
    return {
        "id": conn.id,
        "step_num": step_num,
        "label": conn.label,
        "from_component": conn.from_.component,
        "from_pin": conn.from_.pin,
        "from_name": from_comp.name,
        "to_component": conn.to.component,
        "to_pin": conn.to.pin,
        "to_name": to_comp.name,
        "wire_gauge": conn.wire.gauge_awg,
        "wire_color": color,
        "wire_color_css": _WIRE_CSS.get(color.lower(), "#aaa"),
        "wire_length_mm": conn.wire.length_mm,
        "test_method": conn.commissioning.test_method,
        "test_notes": conn.commissioning.notes,
        "expected_value": conn.commissioning.expected_value,
        "tolerance": conn.commissioning.tolerance,
        "instrument": conn.commissioning.instrument,
        "notes": conn.notes,
        "status": status,
    }


def _progress(manifest: Manifest, state: dict[str, str]) -> dict[str, Any]:
    total = len(manifest.connections)
    passed  = sum(1 for c in manifest.connections if state.get(c.id) == "pass")
    failed  = sum(1 for c in manifest.connections if state.get(c.id) == "fail")
    skipped = sum(1 for c in manifest.connections if state.get(c.id) == "skip")
    done = passed + failed + skipped
    pct = round(done / total * 100) if total else 0
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "done": done,
        "pct": pct,
    }


def create_app(manifest: Manifest) -> FastAPI:
    app = FastAPI(title="Crimp commissioning UI")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # In-memory state: conn_id → 'pass' | 'fail' | 'skip' | (missing = pending)
    state: dict[str, str] = {}

    # Build phase structure once
    phases: list[dict] = []
    seen_phases: dict[str, list] = {}
    step_map: dict[str, int] = {}

    step_n = 1
    for conn in manifest.connections:
        phase = _phase_name(conn.assembly_order)
        if phase not in seen_phases:
            seen_phases[phase] = []
        seen_phases[phase].append(conn)
        step_map[conn.id] = step_n
        step_n += 1

    for phase_name in _PHASE_ORDER:
        if phase_name in seen_phases:
            phases.append({"name": phase_name, "connections": seen_phases[phase_name]})

    tested = sum(1 for c in manifest.connections if c.commissioning.test_method != "none")

    def base_ctx(request: Request) -> dict:
        return {
            "request": request,
            "project_name": manifest.project.name,
            "revision": manifest.project.revision or "",
            "progress": _progress(manifest, state),
        }

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        ctx = base_ctx(request)
        ctx.update({
            "phases": [
                {
                    "name": p["name"],
                    "connections": [
                        _conn_ctx(manifest, c, step_map[c.id], state.get(c.id, "pending"))
                        for c in p["connections"]
                    ],
                }
                for p in phases
            ],
            "total": len(manifest.connections),
            "tested": tested,
            "components": len(manifest.components),
            "state": state,
        })
        return templates.TemplateResponse(request, "index.html", ctx)

    @app.post("/step/{conn_id}/{action}", response_class=HTMLResponse)
    async def set_step(request: Request, conn_id: str, action: str):
        if action not in ("pass", "fail", "skip", "reset"):
            return HTMLResponse("bad action", status_code=400)

        conn = next((c for c in manifest.connections if c.id == conn_id), None)
        if conn is None:
            return HTMLResponse("not found", status_code=404)

        if action == "reset":
            state.pop(conn_id, None)
            new_status = "pending"
        else:
            state[conn_id] = action
            new_status = action

        conn_data = _conn_ctx(manifest, conn, step_map[conn_id], new_status)
        ctx = base_ctx(request)
        ctx["conn"] = conn_data
        return templates.TemplateResponse(request, "step_card.html", ctx)

    @app.get("/summary")
    async def summary():
        return JSONResponse(_progress(manifest, state))

    return app
