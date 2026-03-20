"""Generator: Bill of Materials in Markdown."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from crimp.manifest import Manifest


def _wire_bom(manifest: Manifest) -> list[tuple[str, str, str, str, str]]:
    """Return rows for the wire section: (gauge, colour, runs, total_length, notes).

    Aggregates by (gauge_awg, color). Length shown as '?' when not all runs
    have length_mm set.
    """
    # group by (gauge, color)
    runs: dict[tuple, int] = defaultdict(int)
    lengths_mm: dict[tuple, int] = defaultdict(int)
    missing_len: dict[tuple, int] = defaultdict(int)
    notes_map: dict[tuple, str] = {}

    for conn in manifest.connections:
        w = conn.wire
        key = (w.gauge_awg, w.color)
        if key == (None, ""):
            continue
        runs[key] += 1
        if w.length_mm:
            lengths_mm[key] += w.length_mm
        else:
            missing_len[key] += 1
        # pick up notes from wire_standard if ref present
        if w.ref and w.ref in manifest.wire_standards and key not in notes_map:
            notes_map[key] = manifest.wire_standards[w.ref].notes

    rows = []
    for key in sorted(runs.keys(), key=lambda k: (k[0] or 999, k[1])):
        gauge, color = key
        gauge_str = f"{gauge} AWG" if gauge else "?"
        total = lengths_mm[key]
        n_missing = missing_len[key]
        if n_missing == 0:
            # add 20% cut waste
            length_str = f"{total} mm ({total / 1000:.2f} m) + 20% cut waste"
        elif total > 0:
            length_str = f"≥ {total} mm measured + {n_missing} runs unmeasured"
        else:
            length_str = f"{runs[key]} runs (lengths TBD)"
        rows.append((gauge_str, color, str(runs[key]), length_str, notes_map.get(key, "")))

    return rows


def _render(manifest: Manifest) -> str:
    lines: list[str] = []

    lines.append(f"# {manifest.project.name} — Bill of Materials")
    lines.append("")
    lines.append(manifest.project.description)
    lines.append("")
    if manifest.project.revision:
        lines.append(f"**Revision:** {manifest.project.revision}")
        lines.append("")

    lines.append(
        "> This BOM is generated from the manifest. Wire lengths marked 'TBD' need "
        "field measurement before purchasing."
    )
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 1: Components
    # ------------------------------------------------------------------ #
    lines.append("## Components")
    lines.append("")
    lines.append("| ID | Name | Type | Notes |")
    lines.append("|----|------|------|-------|")
    for comp_id, comp in manifest.components.items():
        notes = comp.notes[:60] + "…" if len(comp.notes) > 60 else comp.notes
        lines.append(f"| `{comp_id}` | {comp.name} | {comp.type} | {notes or '—'} |")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 2: Wire
    # ------------------------------------------------------------------ #
    lines.append("## Wire")
    lines.append("")
    wire_rows = _wire_bom(manifest)
    if wire_rows:
        lines.append("| Gauge | Colour | Runs | Total length | Notes |")
        lines.append("|-------|--------|------|--------------|-------|")
        for gauge, color, runs, length, notes in wire_rows:
            lines.append(f"| {gauge} | {color} | {runs} | {length} | {notes or '—'} |")
    else:
        lines.append("_No wire data found in manifest._")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section 3: Connectors (from component connector specs)
    # ------------------------------------------------------------------ #
    connector_comps = [
        (cid, comp)
        for cid, comp in manifest.components.items()
        if comp.connector and comp.connector.type
    ]
    if connector_comps:
        lines.append("## Connectors")
        lines.append("")
        lines.append("| Component | Connector type | Position | Pins |")
        lines.append("|-----------|---------------|----------|------|")
        for cid, comp in connector_comps:
            c = comp.connector
            pin_str = ", ".join(c.pin_order) if c.pin_order else "—"
            lines.append(f"| `{cid}` ({comp.name}) | {c.type} | {c.position} | {pin_str} |")
        lines.append("")

    # ------------------------------------------------------------------ #
    # Section 4: BOM overrides (manual additions)
    # ------------------------------------------------------------------ #
    if manifest.bom_overrides:
        lines.append("## Additional hardware")
        lines.append("")
        lines.append("_Items that don't appear as connections but are needed for assembly._")
        lines.append("")
        lines.append("| Qty | Unit | Description | Source notes |")
        lines.append("|-----|------|-------------|--------------|")
        for b in manifest.bom_overrides:
            lines.append(f"| {b.qty} | {b.unit or '—'} | {b.description} | {b.source_notes or '—'} |")
        lines.append("")

    return "\n".join(lines)


def generate(manifest: Manifest, output_dir: Path) -> Path:
    """Write bom.md into output_dir. Returns path written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "bom.md"
    out_path.write_text(_render(manifest))
    return out_path
