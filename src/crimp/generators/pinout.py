"""Generator: per-component pinout docs in Markdown."""

from __future__ import annotations

from pathlib import Path

from crimp.manifest import Manifest


_SIGNAL_ICONS = {
    "power": "⚡",
    "ground": "⏚",
    "ac_power": "⚡",
    "digital_in": "→",
    "digital_out": "←",
    "analog_in": "~→",
    "analog_out": "~←",
    "i2c_sda": "I²C",
    "i2c_scl": "I²C",
    "uart_tx": "TX",
    "uart_rx": "RX",
    "pwm": "PWM",
    "spi_mosi": "SPI",
    "spi_miso": "SPI",
    "spi_clk": "SPI",
    "spi_cs": "SPI",
    "usb": "USB",
    "ethernet": "ETH",
    "motor_power": "M",
    "nc_contact": "NC",
    "no_contact": "NO",
    "reset": "RST",
    "other": "?",
    "nc": "—",
}


def _connections_for_pin(
    manifest: Manifest, comp_id: str, pin_id: str
) -> list[str]:
    """Return list of 'other_comp.other_pin (conn_id)' strings for a pin."""
    results = []
    for conn in manifest.connections:
        if conn.from_.component == comp_id and conn.from_.pin == pin_id:
            results.append(f"{conn.to.component}.{conn.to.pin} (`{conn.id}`)")
        elif conn.to.component == comp_id and conn.to.pin == pin_id:
            results.append(f"{conn.from_.component}.{conn.from_.pin} (`{conn.id}`)")
    return results


def _render_component(manifest: Manifest, comp_id: str) -> str:
    comp = manifest.components[comp_id]
    lines: list[str] = []

    lines.append(f"# {comp.name}")
    lines.append("")
    if comp.description:
        lines.append(comp.description)
        lines.append("")

    meta_rows = [
        ("ID", f"`{comp_id}`"),
        ("Type", comp.type),
    ]
    if comp.voltage_logic is not None:
        meta_rows.append(("Logic voltage", f"{comp.voltage_logic} V"))
    if comp.connector:
        meta_rows.append(("Connector", comp.connector.type or "—"))
    if comp.datasheet_url:
        meta_rows.append(("Datasheet", f"[link]({comp.datasheet_url})"))

    lines.append("## Overview")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    for label, value in meta_rows:
        lines.append(f"| {label} | {value} |")
    lines.append("")

    # Pin table
    lines.append("## Pins")
    lines.append("")
    lines.append("| Pin | Signal type | Direction | Function | Rail | Connected to |")
    lines.append("|-----|-------------|-----------|----------|------|--------------|")

    for pin_id, pin in comp.pins.items():
        icon = _SIGNAL_ICONS.get(pin.signal_type, "?")
        signal_cell = f"{icon} `{pin.signal_type}`"
        rail_cell = f"`{pin.voltage_rail}`" if pin.voltage_rail else "—"
        conns = _connections_for_pin(manifest, comp_id, pin_id)
        conn_cell = ", ".join(conns) if conns else "—"
        if pin.physical_label and pin.physical_label != pin_id:
            label_cell = f"{pin_id} ({pin.physical_label})"
        else:
            label_cell = pin_id
        lines.append(
            f"| {label_cell} | {signal_cell} | {pin.direction} | {pin.function} | {rail_cell} | {conn_cell} |"
        )

    if comp.notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        lines.append(comp.notes)

    lines.append("")
    return "\n".join(lines)


def _render_index(manifest: Manifest) -> str:
    lines: list[str] = []
    lines.append(f"# {manifest.project.name} — Pinout Reference")
    lines.append("")
    lines.append(manifest.project.description)
    lines.append("")
    if manifest.project.revision:
        lines.append(f"**Revision:** {manifest.project.revision}")
        lines.append("")

    lines.append("## Components")
    lines.append("")
    lines.append("| ID | Name | Type | Pins |")
    lines.append("|----|------|------|------|")
    for comp_id, comp in manifest.components.items():
        lines.append(
            f"| [{comp_id}]({comp_id}.md) | {comp.name} | {comp.type} | {len(comp.pins)} |"
        )

    if manifest.power_rails:
        lines.append("")
        lines.append("## Power Rails")
        lines.append("")
        lines.append("| Rail | Voltage | Source | Max current |")
        lines.append("|------|---------|--------|-------------|")
        for rail_id, rail in manifest.power_rails.items():
            amps = f"{rail.max_current_a} A" if rail.max_current_a else "—"
            lines.append(
                f"| `{rail_id}` | {rail.voltage_nominal} V | `{rail.source_component}` | {amps} |"
            )

    lines.append("")
    return "\n".join(lines)


def generate(manifest: Manifest, output_dir: Path) -> list[Path]:
    """Write pinout markdown files into output_dir/pinout/.

    Returns list of files written.
    """
    out = output_dir / "pinout"
    out.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    # Index
    index_path = out / "index.md"
    index_path.write_text(_render_index(manifest))
    written.append(index_path)

    # One file per component
    for comp_id in manifest.components:
        comp_path = out / f"{comp_id}.md"
        comp_path.write_text(_render_component(manifest, comp_id))
        written.append(comp_path)

    return written
