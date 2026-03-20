"""Generator: WireViz harness diagrams, one per phase.

Produces SVG wiring diagrams for phases that are small enough to render
clearly (≤ 20 wire connections). Phases with too many components or
non-physical signal connections (USB, Ethernet) are skipped with a note.

Requires: pip install 'crimp-manifest[diagrams]'
"""

from __future__ import annotations

from pathlib import Path

from crimp.manifest import Connection, Manifest

# Signal types that don't produce a physical wire diagram
_SKIP_SIGNAL_TYPES = {"usb", "ethernet", "nc", "reset"}

# WireViz color codes (subset)
_WV_COLOR = {
    "red":    "RD",
    "black":  "BK",
    "blue":   "BU",
    "yellow": "YE",
    "white":  "WH",
    "orange": "OG",
    "green":  "GN",
    "brown":  "BN",
    "purple": "VT",
    "grey":   "GY",
    "gray":   "GY",
    "pink":   "PK",
}

_MAX_WIRES_PER_DIAGRAM = 20


def _phase_name(order: int) -> str:
    from crimp.generators.assembly import _phase_name as _pn
    return _pn(order)


def _safe_id(s: str) -> str:
    """Make a WireViz-safe identifier (letters, digits, underscores only)."""
    return "".join(c if c.isalnum() else "_" for c in s)


def _wv_color(color: str) -> str:
    return _WV_COLOR.get(color.lower(), "")


def _build_harness(
    manifest: Manifest, conns: list[Connection]
) -> dict | None:
    """Build a WireViz harness dict for a list of connections.

    Returns None if the phase should be skipped (too large, or all
    connections are non-wire signal types).
    """
    # Filter out non-physical connections
    wire_conns = [
        c for c in conns
        if manifest.components[c.from_.component].pins.get(c.from_.pin) and
        manifest.components[c.from_.component].pins[c.from_.pin].signal_type
        not in _SKIP_SIGNAL_TYPES
    ]

    if not wire_conns:
        return None
    if len(wire_conns) > _MAX_WIRES_PER_DIAGRAM:
        return None

    # Collect all unique component endpoints
    comp_pins: dict[str, set[str]] = {}
    for conn in wire_conns:
        comp_pins.setdefault(conn.from_.component, set()).add(conn.from_.pin)
        comp_pins.setdefault(conn.to.component, set()).add(conn.to.pin)

    # Build connectors dict
    connectors: dict[str, dict] = {}
    for comp_id, pins in comp_pins.items():
        comp = manifest.components[comp_id]
        pin_list = sorted(pins)
        entry: dict = {
            "pincount": len(pin_list),
            "pins": pin_list,
            "type": comp.type,
        }
        if comp.connector and comp.connector.type:
            entry["type"] = comp.connector.type
        connectors[_safe_id(comp_id)] = entry

    # Build cables + connections
    # Each connection → one cable with one wire
    cables: dict[str, dict] = {}
    connections: list[list] = []

    for conn in wire_conns:
        cable_id = _safe_id(conn.id)
        color_code = _wv_color(conn.wire.color)

        cables[cable_id] = {
            "wirecount": 1,
            "gauge": conn.wire.gauge_awg or 22,
            "gauge_unit": "AWG",
            **({"colors": [color_code]} if color_code else {}),
            **({"length": round(conn.wire.length_mm / 1000, 2)} if conn.wire.length_mm else {}),
        }

        from_id = _safe_id(conn.from_.component)
        to_id   = _safe_id(conn.to.component)
        connections.append([
            {from_id: [conn.from_.pin]},
            {cable_id: [1]},
            {to_id: [conn.to.pin]},
        ])

    return {
        "connectors": connectors,
        "cables": cables,
        "connections": connections,
    }


def generate(manifest: Manifest, output_dir: Path) -> list[Path]:
    """Generate one SVG diagram per phase into output_dir/diagrams/.

    Returns list of files written. Phases that are too large or contain
    only non-wire connections are skipped.
    """
    try:
        from wireviz.wireviz import parse as wv_parse
    except ImportError:
        raise RuntimeError(
            "wireviz not installed. Run: pip install 'crimp-manifest[diagrams]'"
        )

    out = output_dir / "diagrams"
    out.mkdir(parents=True, exist_ok=True)

    # Group connections by phase
    phases: dict[str, list[Connection]] = {}
    for conn in manifest.connections:
        phase = _phase_name(conn.assembly_order)
        phases.setdefault(phase, []).append(conn)

    written: list[Path] = []
    skipped: list[str] = []

    for phase_name, conns in phases.items():
        harness = _build_harness(manifest, conns)
        if harness is None:
            skipped.append(phase_name)
            continue

        slug = phase_name.lower().replace(" ", "_").replace("—", "").replace("/", "_")
        slug = "".join(c if c.isalnum() or c == "_" else "" for c in slug)
        slug = slug.strip("_")

        svg_path = out / f"{slug}.svg"
        try:
            svg_data = wv_parse(harness, return_types="svg")
            svg_path.write_bytes(svg_data if isinstance(svg_data, bytes) else svg_data.encode())
            written.append(svg_path)
        except Exception as e:
            # Don't let one bad phase kill the whole generator
            skipped.append(f"{phase_name} (error: {e})")

    # Write a summary index
    index_lines = [
        f"# {manifest.project.name} — Wiring Diagrams\n",
        "",
        "| Phase | Diagram |",
        "|-------|---------|",
    ]
    for path in written:
        phase_display = path.stem.replace("_", " ").title()
        index_lines.append(f"| {phase_display} | [{path.name}]({path.name}) |")
    for s in skipped:
        index_lines.append(f"| {s} | _(skipped — too large or no wire connections)_ |")
    index_lines.append("")

    index_path = out / "index.md"
    index_path.write_text("\n".join(index_lines))
    written.append(index_path)

    return written
