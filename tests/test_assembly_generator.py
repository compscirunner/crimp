"""Tests for the assembly guide generator."""

from pathlib import Path

import pytest

from crimp.manifest import load
from crimp.generators import assembly as assembly_gen

SCOUT = Path(__file__).parent.parent / "examples" / "scout-robot" / "manifest.json"


@pytest.fixture(scope="module")
def scout():
    return load(SCOUT)


@pytest.fixture(scope="module")
def guide_text(tmp_path_factory, scout):
    out = tmp_path_factory.mktemp("assembly")
    assembly_gen.generate(scout, out)
    return (out / "assembly-guide.md").read_text()


class TestAssemblyGuide:
    def test_file_created(self, tmp_path, scout):
        path = assembly_gen.generate(scout, tmp_path)
        assert path.exists()
        assert path.name == "assembly-guide.md"

    def test_contains_project_name(self, guide_text, scout):
        assert scout.project.name in guide_text

    def test_contains_all_connection_ids(self, guide_text, scout):
        for conn in scout.connections:
            assert conn.id in guide_text, f"Connection {conn.id} missing from guide"

    def test_contains_all_labels(self, guide_text, scout):
        for conn in scout.connections:
            assert conn.label in guide_text, f"Label '{conn.label}' missing from guide"

    def test_wire_standards_section(self, guide_text, scout):
        assert "## Wire Standards" in guide_text
        for ws_id in scout.wire_standards:
            assert ws_id in guide_text

    def test_phases_present(self, guide_text):
        assert "Phase 1" in guide_text
        assert "Phase 2" in guide_text

    def test_power_before_signal(self, guide_text):
        """Phase 1 (power) must appear before Phase 2 (sensors) in the doc."""
        assert guide_text.index("Phase 1") < guide_text.index("Phase 2")

    def test_commissioning_tests_shown(self, guide_text):
        assert "voltage" in guide_text
        assert "continuity" in guide_text
        assert "i2c_scan" in guide_text
        assert "gpio_toggle" in guide_text

    def test_step_numbers_sequential(self, guide_text, scout):
        import re
        steps = re.findall(r"### Step (\d+)", guide_text)
        assert len(steps) == len(scout.connections)
        assert [int(s) for s in steps] == list(range(1, len(scout.connections) + 1))

    def test_batt_step_has_multimeter(self, guide_text):
        assert "multimeter" in guide_text

    def test_i2c_step_shows_expected_address(self, guide_text):
        assert "0x36" in guide_text
