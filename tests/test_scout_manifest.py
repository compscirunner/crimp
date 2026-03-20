"""Integration tests for the Scout robot manifest.

These tests verify that the Scout manifest is internally consistent,
fully specified, and matches known hardware facts about the robot.
"""

from pathlib import Path

import pytest

from crimp.manifest import load, Manifest

SCOUT = Path(__file__).parent.parent / "examples" / "scout-robot" / "manifest.json"


@pytest.fixture(scope="module")
def scout() -> Manifest:
    return load(SCOUT)


# ---------------------------------------------------------------------------
# Basic integrity
# ---------------------------------------------------------------------------


class TestIntegrity:
    def test_loads_without_error(self, scout):
        assert scout is not None

    def test_component_count(self, scout):
        assert len(scout.components) == 37

    def test_connection_count(self, scout):
        assert len(scout.connections) == 65

    def test_no_other_signal_types(self, scout):
        """Every pin must have a specific signal_type — 'other' is a gap marker."""
        other = [
            f"{cid}.{pid}"
            for cid, comp in scout.components.items()
            for pid, pin in comp.pins.items()
            if pin.signal_type == "other"
        ]
        assert other == [], f"Pins still using signal_type=other: {other}"

    def test_all_connections_sorted_by_assembly_order(self, scout):
        orders = [c.assembly_order for c in scout.connections]
        assert orders == sorted(orders)

    def test_all_connections_have_assembly_order(self, scout):
        defaulted = [c.id for c in scout.connections if c.assembly_order == 9999]
        assert defaulted == [], f"Connections with defaulted assembly_order: {defaulted}"

    def test_all_connections_have_labels(self, scout):
        """Every connection should have a human-readable label."""
        missing = [c.id for c in scout.connections if not c.label]
        assert missing == [], f"Connections missing labels: {missing}"

    def test_no_broken_wire_refs(self, scout):
        bad = [
            c.id for c in scout.connections
            if c.wire.ref and c.wire.ref not in scout.wire_standards
        ]
        assert bad == []

    def test_no_broken_voltage_rail_refs(self, scout):
        bad = [
            f"{cid}.{pid}"
            for cid, comp in scout.components.items()
            for pid, pin in comp.pins.items()
            if pin.voltage_rail and pin.voltage_rail not in scout.power_rails
        ]
        assert bad == []


# ---------------------------------------------------------------------------
# Known hardware facts — Pico
# ---------------------------------------------------------------------------


class TestPico:
    def test_pico_exists(self, scout):
        assert "pico" in scout.components

    def test_pico_is_mcu(self, scout):
        assert scout.components["pico"].type == "mcu"

    def test_pico_voltage_logic(self, scout):
        assert scout.components["pico"].voltage_logic == 3.3

    def test_pico_i2c0_sda_on_gp4(self, scout):
        pin = scout.components["pico"].pins["GP4"]
        assert pin.signal_type == "i2c_sda"

    def test_pico_i2c0_scl_on_gp5(self, scout):
        pin = scout.components["pico"].pins["GP5"]
        assert pin.signal_type == "i2c_scl"

    def test_pico_i2c1_sda_on_gp6(self, scout):
        pin = scout.components["pico"].pins["GP6"]
        assert pin.signal_type == "i2c_sda"

    def test_pico_i2c1_scl_on_gp7(self, scout):
        pin = scout.components["pico"].pins["GP7"]
        assert pin.signal_type == "i2c_scl"

    def test_pico_ibus_rx_on_gp9(self, scout):
        pin = scout.components["pico"].pins["GP9"]
        assert pin.signal_type == "uart_rx"

    def test_pico_relay_pins_gp10_to_gp17(self, scout):
        for gp in [f"GP{n}" for n in range(10, 18)]:
            pin = scout.components["pico"].pins[gp]
            assert pin.signal_type == "digital_out", f"{gp} should be digital_out"

    def test_pico_pwm_pins_gp18_to_gp22(self, scout):
        for gp in ["GP18", "GP19", "GP20", "GP21", "GP22"]:
            pin = scout.components["pico"].pins[gp]
            assert pin.signal_type == "pwm", f"{gp} should be pwm"

    def test_pico_spare_pins_are_nc(self, scout):
        for gp in ["GP0", "GP1", "GP2", "GP3", "GP8"]:
            pin = scout.components["pico"].pins[gp]
            assert pin.signal_type == "nc", f"{gp} should be nc"

    def test_pico_vsys_on_5v_rail(self, scout):
        assert scout.components["pico"].pins["VSYS"].voltage_rail == "5v_logic"

    def test_pico_3v3_out_on_3v3_rail(self, scout):
        assert scout.components["pico"].pins["3V3_OUT"].voltage_rail == "3v3_pico"


# ---------------------------------------------------------------------------
# Known hardware facts — encoders
# ---------------------------------------------------------------------------


class TestEncoders:
    def test_both_encoders_exist(self, scout):
        assert "as5600_left" in scout.components
        assert "as5600_right" in scout.components

    def test_encoders_on_different_i2c_buses(self, scout):
        """AS5600 has fixed address 0x36 — must be on separate buses."""
        left_sda = next(
            c for c in scout.connections
            if c.id == "enc_left_sda"
        )
        right_sda = next(
            c for c in scout.connections
            if c.id == "enc_right_sda"
        )
        assert left_sda.from_.pin != right_sda.from_.pin, \
            "Left and right encoders must use different Pico I2C pins (different buses)"

    def test_left_encoder_on_i2c0(self, scout):
        conn = next(c for c in scout.connections if c.id == "enc_left_sda")
        assert conn.from_.pin == "GP4"

    def test_right_encoder_on_i2c1(self, scout):
        conn = next(c for c in scout.connections if c.id == "enc_right_sda")
        assert conn.from_.pin == "GP6"

    def test_encoders_have_jst_ph4_connector(self, scout):
        for enc in ("as5600_left", "as5600_right"):
            conn = scout.components[enc].connector
            assert conn is not None
            assert "JST-PH" in conn.type

    def test_encoder_vcc_wires_are_red(self, scout):
        for conn_id in ("enc_left_vcc", "enc_right_vcc"):
            conn = next(c for c in scout.connections if c.id == conn_id)
            assert conn.wire.color == "red"

    def test_encoder_sda_wires_are_blue(self, scout):
        for conn_id in ("enc_left_sda", "enc_right_sda"):
            conn = next(c for c in scout.connections if c.id == conn_id)
            assert conn.wire.color == "blue"


# ---------------------------------------------------------------------------
# Known hardware facts — power
# ---------------------------------------------------------------------------


class TestPower:
    def test_three_power_rails(self, scout):
        assert set(scout.power_rails.keys()) == {"12v_main", "5v_logic", "3v3_pico"}

    def test_12v_rail_from_bp65(self, scout):
        assert scout.power_rails["12v_main"].source_component == "bp65"

    def test_5v_rail_from_step_down(self, scout):
        assert scout.power_rails["5v_logic"].source_component == "step_down_5v"

    def test_battery_connects_to_fuse(self, scout):
        conn = next(c for c in scout.connections if c.id == "batt_pos_to_fuse")
        assert conn.from_.component == "battery"
        assert conn.to.component == "inline_fuse_40a"

    def test_main_power_wires_are_10awg(self, scout):
        for conn_id in ("batt_pos_to_fuse", "xt60_pos_to_busbar"):
            conn = next(c for c in scout.connections if c.id == conn_id)
            assert conn.wire.gauge_awg == 10

    def test_assembly_order_power_before_signal(self, scout):
        """Power connections (order < 100) must all come before Pico I2C (order >= 100)."""
        power_ids = {"batt_pos_to_fuse", "bp65_out_to_stepdown_12v", "stepdown_5v_to_pico_vsys"}
        signal_ids = {"enc_left_sda", "enc_right_sda", "ibus_rx"}
        power_orders = [c.assembly_order for c in scout.connections if c.id in power_ids]
        signal_orders = [c.assembly_order for c in scout.connections if c.id in signal_ids]
        assert max(power_orders) < min(signal_orders)


# ---------------------------------------------------------------------------
# Known hardware facts — RC and E-stop
# ---------------------------------------------------------------------------


class TestRC:
    def test_ibus_goes_to_pico(self, scout):
        conn = next(c for c in scout.connections if c.id == "ibus_rx")
        assert conn.to.component == "pico"
        assert conn.to.pin == "GP9"

    def test_rc_estop_bypasses_pico(self, scout):
        """Hardware E-stop must go directly from receiver to motor controller."""
        conn = next(c for c in scout.connections if c.id == "rc_estop_direct")
        assert conn.from_.component == "rc_receiver"
        assert conn.to.component == "pololu_24v12"
        assert conn.to.pin == "rc_in"

    def test_rc_estop_not_routed_through_pico(self, scout):
        conn = next(c for c in scout.connections if c.id == "rc_estop_direct")
        assert conn.from_.component != "pico"
        assert conn.to.component != "pico"


# ---------------------------------------------------------------------------
# Commissioning coverage
# ---------------------------------------------------------------------------


class TestCommissioning:
    def test_power_connections_have_voltage_tests(self, scout):
        power_conns = [
            c for c in scout.connections
            if c.from_.component in ("battery", "bp65", "step_down_5v")
            and c.wire.gauge_awg is not None
            and c.wire.gauge_awg <= 18
        ]
        missing = [
            c.id for c in power_conns
            if c.commissioning.test_method not in ("voltage", "continuity")
        ]
        assert missing == [], f"Power connections missing voltage/continuity tests: {missing}"

    def test_i2c_connections_have_scan_tests(self, scout):
        i2c_conns = [
            c for c in scout.connections
            if "sda" in c.id and c.commissioning.test_method != "none"
        ]
        for conn in i2c_conns:
            assert conn.commissioning.test_method == "i2c_scan", \
                f"{conn.id}: I2C SDA connection should use i2c_scan test"

    def test_relay_connections_have_gpio_toggle_tests(self, scout):
        relay_conns = [c for c in scout.connections if c.id.startswith("relay_in")]
        for conn in relay_conns:
            assert conn.commissioning.test_method == "gpio_toggle", \
                f"{conn.id}: relay connection should use gpio_toggle test"

    def test_all_commissioning_methods_are_valid(self, scout):
        valid = {"continuity", "voltage", "i2c_scan", "uart_loopback",
                 "gpio_toggle", "pwm_measure", "none"}
        invalid = [
            f"{c.id}: {c.commissioning.test_method}"
            for c in scout.connections
            if c.commissioning.test_method not in valid
        ]
        assert invalid == []
