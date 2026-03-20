"""Tests for manifest loading and validation."""

import json
from pathlib import Path

import pytest

from crimp.manifest import (
    Connection,
    Manifest,
    ManifestError,
    load,
    validate_raw,
)

FIXTURES = Path(__file__).parent / "fixtures"
MINIMAL = FIXTURES / "minimal.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def minimal_data() -> dict:
    return json.loads(MINIMAL.read_text())


# ---------------------------------------------------------------------------
# validate_raw
# ---------------------------------------------------------------------------


class TestValidateRaw:
    def test_valid_minimal_passes(self):
        validate_raw(minimal_data())

    def test_missing_required_field_raises(self):
        data = minimal_data()
        del data["project"]
        with pytest.raises(ManifestError, match="validation failed"):
            validate_raw(data)

    def test_invalid_component_type_raises(self):
        data = minimal_data()
        data["components"]["pico"]["type"] = "not_a_valid_type"
        with pytest.raises(ManifestError, match="validation failed"):
            validate_raw(data)

    def test_invalid_signal_type_raises(self):
        data = minimal_data()
        data["components"]["pico"]["pins"]["GP4"]["signal_type"] = "banana"
        with pytest.raises(ManifestError, match="validation failed"):
            validate_raw(data)

    def test_connection_missing_id_raises(self):
        data = minimal_data()
        del data["connections"][0]["id"]
        with pytest.raises(ManifestError, match="validation failed"):
            validate_raw(data)


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------


class TestLoad:
    def test_load_returns_manifest(self):
        m = load(MINIMAL)
        assert isinstance(m, Manifest)

    def test_project_fields(self):
        m = load(MINIMAL)
        assert m.project.name == "Minimal Test Project"
        assert m.project.description == "Simplest possible manifest for testing."

    def test_components_parsed(self):
        m = load(MINIMAL)
        assert "pico" in m.components
        assert "encoder1" in m.components
        assert m.components["pico"].name == "Raspberry Pi Pico"
        assert m.components["pico"].type == "mcu"
        assert m.components["pico"].voltage_logic == 3.3

    def test_pins_parsed(self):
        m = load(MINIMAL)
        pins = m.components["pico"].pins
        assert "GP4" in pins
        assert pins["GP4"].signal_type == "i2c_sda"
        assert pins["GP4"].direction == "bidir"

    def test_connector_parsed(self):
        m = load(MINIMAL)
        conn = m.components["encoder1"].connector
        assert conn is not None
        assert conn.type == "JST-PH-4"
        assert conn.position == "component_side"
        assert conn.pin_order == ["VCC", "GND", "SDA", "SCL"]

    def test_connections_parsed_and_sorted(self):
        m = load(MINIMAL)
        assert len(m.connections) == 3
        orders = [c.assembly_order for c in m.connections]
        assert orders == sorted(orders)

    def test_connection_fields(self):
        m = load(MINIMAL)
        enc1_sda = next(c for c in m.connections if c.id == "enc1_sda")
        assert enc1_sda.label == "ENC1_SDA"
        assert enc1_sda.from_.component == "pico"
        assert enc1_sda.from_.pin == "GP4"
        assert enc1_sda.to.component == "encoder1"
        assert enc1_sda.to.pin == "SDA"
        assert enc1_sda.wire.gauge_awg == 26
        assert enc1_sda.wire.color == "blue"

    def test_wire_standard_ref_resolves(self):
        m = load(MINIMAL)
        enc1_vcc = next(c for c in m.connections if c.id == "enc1_vcc")
        assert enc1_vcc.wire.color == "red"
        assert enc1_vcc.wire.gauge_awg == 26

    def test_commissioning_parsed(self):
        m = load(MINIMAL)
        enc1_vcc = next(c for c in m.connections if c.id == "enc1_vcc")
        assert enc1_vcc.commissioning.test_method == "voltage"
        assert enc1_vcc.commissioning.expected_value == 3.3
        assert enc1_vcc.commissioning.instrument == "multimeter"

    def test_wire_standards_parsed(self):
        m = load(MINIMAL)
        assert "signal_26awg_red" in m.wire_standards
        assert m.wire_standards["signal_26awg_red"].color == "red"

    def test_power_rails_parsed(self):
        m = load(MINIMAL)
        assert "3v3" in m.power_rails
        assert m.power_rails["3v3"].voltage_nominal == 3.3

    def test_bom_overrides_parsed(self):
        m = load(MINIMAL)
        assert len(m.bom_overrides) == 2
        assert m.bom_overrides[0].description == "4.7kΩ resistor (I2C0 SDA pull-up)"
        assert m.bom_overrides[0].qty == 1

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ManifestError, match="not found"):
            load(tmp_path / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ this is not json }")
        with pytest.raises(ManifestError, match="Invalid JSON"):
            load(bad)
