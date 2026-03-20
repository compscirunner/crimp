"""Manifest loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_PATH = Path(__file__).parent.parent.parent / "schema" / "manifest.schema.json"


# ---------------------------------------------------------------------------
# Typed model
# ---------------------------------------------------------------------------


@dataclass
class Pin:
    id: str
    function: str
    signal_type: str
    direction: str
    physical_label: str = ""
    voltage_rail: str = ""
    notes: str = ""


@dataclass
class ConnectorSpec:
    type: str = ""
    position: str = "none"
    pin_order: list[str] = field(default_factory=list)


@dataclass
class Component:
    id: str
    name: str
    type: str
    pins: dict[str, Pin] = field(default_factory=dict)
    description: str = ""
    datasheet_url: str = ""
    voltage_logic: float | None = None
    connector: ConnectorSpec | None = None
    notes: str = ""


@dataclass
class WireSpec:
    ref: str = ""
    gauge_awg: int | None = None
    color: str = ""
    length_mm: int | None = None
    notes: str = ""


@dataclass
class ConnectionEndpoint:
    component: str
    pin: str


@dataclass
class CommissioningSpec:
    test_method: str = "none"
    expected_value: Any = None
    tolerance: Any = None
    instrument: str = "none"
    notes: str = ""


@dataclass
class Connection:
    id: str
    from_: ConnectionEndpoint
    to: ConnectionEndpoint
    wire: WireSpec
    label: str = ""
    assembly_order: int = 9999
    commissioning: CommissioningSpec = field(default_factory=CommissioningSpec)
    notes: str = ""


@dataclass
class PowerRail:
    id: str
    voltage_nominal: float
    source_component: str = ""
    max_current_a: float | None = None
    notes: str = ""


@dataclass
class WireStandard:
    id: str
    gauge_awg: int
    color: str
    notes: str = ""


@dataclass
class BomOverride:
    description: str
    qty: int
    unit: str = ""
    source_notes: str = ""


@dataclass
class Project:
    name: str
    description: str
    revision: str = ""
    notes: str = ""


@dataclass
class Manifest:
    crimp_version: str
    project: Project
    components: dict[str, Component]
    connections: list[Connection]
    wire_standards: dict[str, WireStandard] = field(default_factory=dict)
    power_rails: dict[str, PowerRail] = field(default_factory=dict)
    bom_overrides: list[BomOverride] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------


class ManifestError(Exception):
    """Raised when a manifest cannot be loaded or validated."""


def _load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        raise ManifestError(f"Schema not found at {SCHEMA_PATH}")
    return json.loads(SCHEMA_PATH.read_text())


def validate_raw(data: dict) -> None:
    """Validate a raw manifest dict against the JSON schema.

    Raises ManifestError with a human-readable message on failure.
    """
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        messages = []
        for err in errors:
            path = " → ".join(str(p) for p in err.path) or "(root)"
            messages.append(f"  {path}: {err.message}")
        raise ManifestError("Manifest validation failed:\n" + "\n".join(messages))


def validate_refs(data: dict) -> None:
    """Check referential integrity: connections must reference valid components and pins.

    Also checks wire_standards refs and voltage_rail refs.
    Raises ManifestError listing all broken references found.
    """
    errors = []
    components = data.get("components", {})
    wire_standards = data.get("wire_standards", {})
    power_rails = data.get("power_rails", {})

    for i, conn in enumerate(data.get("connections", [])):
        conn_id = conn.get("id", f"connections[{i}]")

        for side in ("from", "to"):
            endpoint = conn.get(side, {})
            comp_id = endpoint.get("component")
            pin_id = endpoint.get("pin")
            if comp_id not in components:
                errors.append(f"  connection '{conn_id}' {side}.component: '{comp_id}' not found in components")
            elif pin_id not in components[comp_id].get("pins", {}):
                errors.append(f"  connection '{conn_id}' {side}.pin: '{pin_id}' not found in {comp_id}.pins")

        wire_ref = conn.get("wire", {}).get("ref")
        if wire_ref and wire_ref not in wire_standards:
            errors.append(f"  connection '{conn_id}' wire.ref: '{wire_ref}' not found in wire_standards")

    for comp_id, comp in components.items():
        for pin_id, pin in comp.get("pins", {}).items():
            rail_ref = pin.get("voltage_rail")
            if rail_ref and rail_ref not in power_rails:
                errors.append(f"  component '{comp_id}' pin '{pin_id}' voltage_rail: '{rail_ref}' not found in power_rails")

    if errors:
        raise ManifestError("Referential integrity check failed:\n" + "\n".join(errors))


def _parse(data: dict) -> Manifest:
    """Convert a validated raw manifest dict into a typed Manifest."""

    project = Project(
        name=data["project"]["name"],
        description=data["project"]["description"],
        revision=data["project"].get("revision", ""),
        notes=data["project"].get("notes", ""),
    )

    wire_standards = {
        k: WireStandard(
            id=k,
            gauge_awg=v["gauge_awg"],
            color=v["color"],
            notes=v.get("notes", ""),
        )
        for k, v in data.get("wire_standards", {}).items()
    }

    power_rails = {
        k: PowerRail(
            id=k,
            voltage_nominal=v["voltage_nominal"],
            source_component=v.get("source_component", ""),
            max_current_a=v.get("max_current_a"),
            notes=v.get("notes", ""),
        )
        for k, v in data.get("power_rails", {}).items()
    }

    components: dict[str, Component] = {}
    for comp_id, comp_data in data["components"].items():
        pins = {
            pin_id: Pin(
                id=pin_id,
                function=pin_data["function"],
                signal_type=pin_data["signal_type"],
                direction=pin_data["direction"],
                physical_label=pin_data.get("physical_label", ""),
                voltage_rail=pin_data.get("voltage_rail", ""),
                notes=pin_data.get("notes", ""),
            )
            for pin_id, pin_data in comp_data["pins"].items()
        }
        conn_data = comp_data.get("connector")
        connector = (
            ConnectorSpec(
                type=conn_data.get("type", ""),
                position=conn_data.get("position", "none"),
                pin_order=conn_data.get("pin_order", []),
            )
            if conn_data
            else None
        )
        components[comp_id] = Component(
            id=comp_id,
            name=comp_data["name"],
            type=comp_data["type"],
            pins=pins,
            description=comp_data.get("description", ""),
            datasheet_url=comp_data.get("datasheet_url", ""),
            voltage_logic=comp_data.get("voltage_logic"),
            connector=connector,
            notes=comp_data.get("notes", ""),
        )

    connections: list[Connection] = []
    for conn_data in data["connections"]:
        c_spec = conn_data.get("commissioning", {})
        wire_data = conn_data["wire"]

        # Resolve wire standard ref if present
        ref = wire_data.get("ref", "")
        if ref and ref in wire_standards:
            std = wire_standards[ref]
            gauge = wire_data.get("gauge_awg", std.gauge_awg)
            color = wire_data.get("color", std.color)
        else:
            gauge = wire_data.get("gauge_awg")
            color = wire_data.get("color", "")

        connections.append(
            Connection(
                id=conn_data["id"],
                label=conn_data.get("label", ""),
                from_=ConnectionEndpoint(
                    component=conn_data["from"]["component"],
                    pin=conn_data["from"]["pin"],
                ),
                to=ConnectionEndpoint(
                    component=conn_data["to"]["component"],
                    pin=conn_data["to"]["pin"],
                ),
                wire=WireSpec(
                    ref=ref,
                    gauge_awg=gauge,
                    color=color,
                    length_mm=wire_data.get("length_mm"),
                    notes=wire_data.get("notes", ""),
                ),
                assembly_order=conn_data.get("assembly_order", 9999),
                commissioning=CommissioningSpec(
                    test_method=c_spec.get("test_method", "none"),
                    expected_value=c_spec.get("expected_value"),
                    tolerance=c_spec.get("tolerance"),
                    instrument=c_spec.get("instrument", "none"),
                    notes=c_spec.get("notes", ""),
                ),
                notes=conn_data.get("notes", ""),
            )
        )

    # Sort by assembly_order
    connections.sort(key=lambda c: c.assembly_order)

    bom_overrides = [
        BomOverride(
            description=b["description"],
            qty=b["qty"],
            unit=b.get("unit", ""),
            source_notes=b.get("source_notes", ""),
        )
        for b in data.get("bom_overrides", [])
    ]

    return Manifest(
        crimp_version=data["crimp_version"],
        project=project,
        components=components,
        connections=connections,
        wire_standards=wire_standards,
        power_rails=power_rails,
        bom_overrides=bom_overrides,
    )


def load(path: Path | str) -> Manifest:
    """Load, validate, and parse a manifest file. Returns a typed Manifest.

    Raises ManifestError on any failure.
    """
    path = Path(path)
    if not path.exists():
        raise ManifestError(f"Manifest not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ManifestError(f"Invalid JSON in manifest: {e}") from e

    validate_raw(data)
    validate_refs(data)
    return _parse(data)
