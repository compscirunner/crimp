"""Tests for the commissioning test script generator."""

from pathlib import Path

import pytest

from crimp.manifest import load
from crimp.generators import commissioning as comm_gen

SCOUT = Path(__file__).parent.parent / "examples" / "scout-robot" / "manifest.json"


@pytest.fixture(scope="module")
def scout():
    return load(SCOUT)


@pytest.fixture(scope="module")
def comm_text(tmp_path_factory, scout):
    out = tmp_path_factory.mktemp("comm")
    comm_gen.generate(scout, out)
    return (out / "commissioning_tests.py").read_text()


class TestCommissioningGenerator:
    def test_file_created(self, tmp_path, scout):
        path = comm_gen.generate(scout, tmp_path)
        assert path.exists()
        assert path.name == "commissioning_tests.py"

    def test_is_valid_python(self, tmp_path, scout):
        path = comm_gen.generate(scout, tmp_path)
        source = path.read_text()
        compile(source, str(path), "exec")  # raises SyntaxError if invalid

    def test_one_function_per_connection(self, comm_text, scout):
        for conn in scout.connections:
            assert f"def test_{conn.id}(" in comm_text, f"Missing test for {conn.id}"

    def test_voltage_stub_has_assert(self, comm_text):
        assert "abs(measured_v -" in comm_text

    def test_continuity_stub_present(self, comm_text):
        assert "Continuity check failed" in comm_text

    def test_i2c_scan_stub_has_address(self, comm_text):
        assert "0x36" in comm_text
        assert "i2c.scan()" in comm_text

    def test_i2c_bus_pin_numbers_correct(self, comm_text):
        # I2C0: SDA=GP4, SCL=GP5
        assert "sda=Pin(4)" in comm_text
        assert "scl=Pin(5)" in comm_text

    def test_gpio_toggle_stub_present(self, comm_text):
        assert "GPIO toggle test failed" in comm_text

    def test_pwm_stub_present(self, comm_text):
        assert "PWM signal not detected" in comm_text

    def test_uart_stub_present(self, comm_text):
        assert "UART loopback failed" in comm_text

    def test_none_tests_use_skip(self, comm_text):
        assert "pytest.skip" in comm_text

    def test_phase_comments_present(self, comm_text):
        assert "Phase 1" in comm_text
        assert "Phase 2" in comm_text

    def test_import_pytest(self, comm_text):
        assert "import pytest" in comm_text
