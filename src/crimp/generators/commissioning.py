"""Generator: pytest commissioning test stubs from manifest commissioning specs."""

from __future__ import annotations

from pathlib import Path

from crimp.manifest import Connection, Manifest

# ---------------------------------------------------------------------------
# Per-method stub bodies
# ---------------------------------------------------------------------------

_STUB_VOLTAGE = '''\
    # Instrument: {instrument}
    # {notes}
    #
    # HOW TO TEST:
    #   1. Ensure power is on and connection is made.
    #   2. Set multimeter to DC voltage mode.
    #   3. Probe FROM {from_comp}.{from_pin} — TO {to_comp}.{to_pin}.
    #   4. Expected: {expected} V  (tolerance ±{tolerance})
    #
    measured_v = None  # TODO: replace with instrument reading or manual input
    assert measured_v is not None, "Set measured_v to the voltage you read"
    assert abs(measured_v - {expected}) <= {tolerance}, (
        f"Voltage out of range: {{measured_v}} V (expected {expected} ±{tolerance} V)"
    )\
'''

_STUB_CONTINUITY = '''\
    # Instrument: {instrument}
    # {notes}
    #
    # HOW TO TEST:
    #   1. Power OFF before probing.
    #   2. Set multimeter to continuity / resistance mode.
    #   3. Probe FROM {from_comp}.{from_pin} — TO {to_comp}.{to_pin}.
    #   4. Expect: beep / < 1 Ω.
    #
    connected = None  # TODO: True if meter beeps, False otherwise
    assert connected is True, "Continuity check failed — check crimp and wire run"\
'''

_STUB_I2C_SCAN = '''\
    # Instrument: {instrument}
    # {notes}
    #
    # HOW TO TEST (MicroPython on Pico):
    #   from machine import I2C, Pin
    #   i2c = I2C({bus_id}, sda=Pin({sda_pin_num}), scl=Pin({scl_pin_num}))
    #   devices = i2c.scan()
    #   print([hex(d) for d in devices])
    #
    # Expected address: {expected}
    #
    found_addresses = []  # TODO: populate from i2c.scan() result
    expected_addr = {expected_int}
    assert expected_addr in found_addresses, (
        f"Device {expected} not found on I2C bus. Found: {{[hex(a) for a in found_addresses]}}"
    )\
'''

_STUB_GPIO_TOGGLE = '''\
    # Instrument: {instrument}
    # {notes}
    #
    # HOW TO TEST:
    #   Drive {from_comp}.{from_pin} and observe {to_comp}.{to_pin}.
    #
    toggled = None  # TODO: True if output responded as expected
    assert toggled is True, "GPIO toggle test failed — check wiring and logic level"\
'''

_STUB_PWM_MEASURE = '''\
    # Instrument: {instrument}
    # {notes}
    #
    # HOW TO TEST:
    #   1. Drive {from_comp}.{from_pin} with a known PWM signal.
    #   2. Probe {to_comp}.{to_pin} with oscilloscope (DSO-2090).
    #   3. Verify frequency and duty cycle match commanded values.
    #
    signal_present = None  # TODO: True if scope shows PWM signal
    assert signal_present is True, "PWM signal not detected — check wiring and transistor board"\
'''

_STUB_UART_LOOPBACK = '''\
    # Instrument: {instrument}
    # {notes}
    #
    # HOW TO TEST:
    #   1. Connect {from_comp}.{from_pin} → {to_comp}.{to_pin}.
    #   2. Send a known byte sequence from one end.
    #   3. Verify the same sequence is received on the other end.
    #
    loopback_ok = None  # TODO: True if echo matches sent bytes
    assert loopback_ok is True, "UART loopback failed — check TX/RX wiring"\
'''

_STUB_NONE = '''\
    # No automated test defined for this connection.
    # Verified visually or as part of another test.
    pytest.skip("No commissioning test defined for {conn_id}")\
'''

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _i2c_bus_info(manifest: Manifest, conn: Connection) -> dict:
    """Extract I2C bus number and pin numbers from the connection endpoints."""
    # from_ is always the Pico side for I2C SDA connections
    pin_id = conn.from_.pin  # e.g. "GP4"
    sda_num = ""
    scl_num = ""
    bus_id = 0

    if pin_id.startswith("GP"):
        try:
            n = int(pin_id[2:])
            sda_num = str(n)
            scl_num = str(n + 1)
            # Pico I2C0: GP4/GP5, I2C1: GP6/GP7
            bus_id = 0 if n < 6 else 1
        except ValueError:
            pass

    return {"bus_id": bus_id, "sda_pin_num": sda_num, "scl_pin_num": scl_num}


def _stub_body(conn: Connection, manifest: Manifest) -> str:
    cm = conn.commissioning
    method = cm.test_method
    notes = cm.notes or "No additional notes."
    instrument = cm.instrument or "none"
    expected = cm.expected_value
    tolerance = cm.tolerance if cm.tolerance is not None else 1

    base = dict(
        from_comp=conn.from_.component,
        from_pin=conn.from_.pin,
        to_comp=conn.to.component,
        to_pin=conn.to.pin,
        conn_id=conn.id,
        notes=notes,
        instrument=instrument,
        expected=expected,
        tolerance=tolerance,
    )

    if method == "voltage":
        return _STUB_VOLTAGE.format(**base)

    if method == "continuity":
        return _STUB_CONTINUITY.format(**base)

    if method == "i2c_scan":
        i2c = _i2c_bus_info(manifest, conn)
        # Convert hex string "0x36" → int for assert
        try:
            expected_int = int(str(expected), 16) if expected else 0
        except ValueError:
            expected_int = 0
        return _STUB_I2C_SCAN.format(**base, **i2c, expected_int=expected_int)

    if method == "gpio_toggle":
        return _STUB_GPIO_TOGGLE.format(**base)

    if method == "pwm_measure":
        return _STUB_PWM_MEASURE.format(**base)

    if method == "uart_loopback":
        return _STUB_UART_LOOPBACK.format(**base)

    return _STUB_NONE.format(**base)


def _test_name(conn_id: str) -> str:
    return f"test_{conn_id}"


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def _render(manifest: Manifest) -> str:
    lines: list[str] = []

    lines.append('"""')
    lines.append(f"Commissioning tests for {manifest.project.name}.")
    lines.append("")
    lines.append("Generated by crimp from manifest.json — DO NOT EDIT by hand.")
    lines.append("Update the manifest commissioning fields and re-run `crimp build`.")
    lines.append('"""')
    lines.append("")
    lines.append("import pytest")
    lines.append("")
    lines.append("")

    # Group by phase for readability
    current_phase = None

    for conn in manifest.connections:
        from crimp.generators.assembly import _phase_name
        phase = _phase_name(conn.assembly_order)

        if phase != current_phase:
            current_phase = phase
            lines.append("")
            lines.append(f"# {'─' * 70}")
            lines.append(f"# {phase}")
            lines.append(f"# {'─' * 70}")
            lines.append("")

        cm = conn.commissioning
        from_comp = manifest.components[conn.from_.component]
        to_comp = manifest.components[conn.to.component]

        lines.append(f"def {_test_name(conn.id)}():")
        lines.append(f'    """{conn.label}')
        lines.append(f"")
        lines.append(f"    Connection : {conn.id}")
        lines.append(f"    From       : {conn.from_.component}.{conn.from_.pin} ({from_comp.name})")
        lines.append(f"    To         : {conn.to.component}.{conn.to.pin} ({to_comp.name})")
        lines.append(f"    Wire       : {conn.wire.gauge_awg or '?'} AWG {conn.wire.color}")
        lines.append(f"    Test method: {cm.test_method}")
        lines.append(f'    """')
        lines.append(_stub_body(conn, manifest))
        lines.append("")
        lines.append("")

    return "\n".join(lines)


def generate(manifest: Manifest, output_dir: Path) -> Path:
    """Write commissioning_tests.py into output_dir. Returns path written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "commissioning_tests.py"
    out_path.write_text(_render(manifest))
    return out_path
