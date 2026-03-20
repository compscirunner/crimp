"""Generator: step-by-step assembly guide in Markdown."""

from __future__ import annotations

from pathlib import Path

from crimp.manifest import Connection, Manifest


# Ranges that map to human-readable phase names.
# Each tuple is (min_order_inclusive, max_order_inclusive, phase_name).
_PHASES = [
    (0,   99,  "Phase 1 — Power wiring"),
    (100, 149, "Phase 2 — I²C / UART / RC sensors"),
    (130, 139, "Phase 2 — Relay board"),       # overlap handled by first-match
    (140, 169, "Phase 3 — PWM outputs & control"),
    (170, 199, "Phase 4 — Network & peripherals"),
    (200, 299, "Phase 5 — AC mains"),
]

# Simpler: derive phases from hundreds + tens groups present in the manifest
# rather than hardcoding ranges — more robust across projects.

_TEST_ICONS = {
    "voltage":       "🔋",
    "continuity":    "🔗",
    "i2c_scan":      "🔍",
    "uart_loopback": "↩️",
    "gpio_toggle":   "💡",
    "pwm_measure":   "📡",
    "none":          "",
}


def _phase_name(order: int) -> str:
    """Derive a phase label from assembly_order.

    Convention used in Scout manifest:
      10-99   → Power
      100-129 → Sensors (I2C / UART / RC)
      130-139 → Relay board
      140-169 → PWM / control signals
      170-199 → Network & peripherals
      200+    → AC mains / charging
    """
    if order < 100:
        return "Phase 1 — Power wiring"
    if order < 130:
        return "Phase 2 — Sensors (I²C / UART / RC)"
    if order < 140:
        return "Phase 3 — Relay board"
    if order < 170:
        return "Phase 4 — PWM & control signals"
    if order < 200:
        return "Phase 5 — Network & peripherals"
    return "Phase 6 — AC mains / charging"


def _wire_desc(conn: Connection) -> str:
    parts = []
    if conn.wire.gauge_awg:
        parts.append(f"{conn.wire.gauge_awg} AWG")
    if conn.wire.color:
        parts.append(conn.wire.color)
    if conn.wire.length_mm:
        parts.append(f"{conn.wire.length_mm} mm")
    return " / ".join(parts) if parts else "—"


def _commissioning_block(conn: Connection) -> list[str]:
    cm = conn.commissioning
    if cm.test_method == "none":
        return []

    icon = _TEST_ICONS.get(cm.test_method, "✓")
    lines = [f"  > **Test ({cm.test_method})** {icon}"]

    if cm.notes:
        lines.append(f"  > {cm.notes}")

    details = []
    if cm.expected_value is not None:
        details.append(f"expected: `{cm.expected_value}`")
    if cm.instrument and cm.instrument != "none":
        details.append(f"instrument: {cm.instrument}")
    if cm.tolerance is not None:
        details.append(f"tolerance: ±{cm.tolerance}")
    if details:
        lines.append(f"  > {' · '.join(details)}")

    return lines


def _render(manifest: Manifest) -> str:
    lines: list[str] = []

    lines.append(f"# {manifest.project.name} — Assembly Guide")
    lines.append("")
    lines.append(manifest.project.description)
    lines.append("")
    if manifest.project.revision:
        lines.append(f"**Revision:** {manifest.project.revision}")
        lines.append("")

    lines.append("> Follow steps in order. Complete each commissioning test before moving on.")
    lines.append("> Wire colour conventions are defined in the Wire Standards table below.")
    lines.append("")

    # Wire standards quick reference
    if manifest.wire_standards:
        lines.append("## Wire Standards")
        lines.append("")
        lines.append("| Ref | Gauge | Colour | Notes |")
        lines.append("|-----|-------|--------|-------|")
        for ws_id, ws in manifest.wire_standards.items():
            lines.append(f"| `{ws_id}` | {ws.gauge_awg} AWG | {ws.color} | {ws.notes or '—'} |")
        lines.append("")

    # Group connections into phases
    phases: dict[str, list[Connection]] = {}
    for conn in manifest.connections:  # already sorted by assembly_order
        phase = _phase_name(conn.assembly_order)
        phases.setdefault(phase, []).append(conn)

    step = 1
    for phase_name, conns in phases.items():
        lines.append(f"## {phase_name}")
        lines.append("")

        for conn in conns:
            from_comp = manifest.components[conn.from_.component]
            to_comp = manifest.components[conn.to.component]

            lines.append(f"### Step {step} — {conn.label}")
            lines.append("")
            lines.append(f"| | |")
            lines.append(f"|---|---|")
            lines.append(f"| **From** | `{conn.from_.component}` · `{conn.from_.pin}` ({from_comp.name}) |")
            lines.append(f"| **To** | `{conn.to.component}` · `{conn.to.pin}` ({to_comp.name}) |")
            lines.append(f"| **Wire** | {_wire_desc(conn)} |")
            if conn.wire.ref:
                lines.append(f"| **Std** | `{conn.wire.ref}` |")
            lines.append(f"| **ID** | `{conn.id}` |")
            if conn.notes:
                lines.append(f"| **Notes** | {conn.notes} |")
            lines.append("")

            comm_lines = _commissioning_block(conn)
            if comm_lines:
                lines.extend(comm_lines)
                lines.append("")

            step += 1

    return "\n".join(lines)


def generate(manifest: Manifest, output_dir: Path) -> Path:
    """Write assembly-guide.md into output_dir.

    Returns the path of the file written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "assembly-guide.md"
    out_path.write_text(_render(manifest))
    return out_path
