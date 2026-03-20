"""Tests for the BOM generator."""

from pathlib import Path

import pytest

from crimp.manifest import load
from crimp.generators import bom as bom_gen

SCOUT = Path(__file__).parent.parent / "examples" / "scout-robot" / "manifest.json"


@pytest.fixture(scope="module")
def scout():
    return load(SCOUT)


@pytest.fixture(scope="module")
def bom_text(tmp_path_factory, scout):
    out = tmp_path_factory.mktemp("bom")
    bom_gen.generate(scout, out)
    return (out / "bom.md").read_text()


class TestBomGenerator:
    def test_file_created(self, tmp_path, scout):
        path = bom_gen.generate(scout, tmp_path)
        assert path.exists()
        assert path.name == "bom.md"

    def test_contains_project_name(self, bom_text, scout):
        assert scout.project.name in bom_text

    def test_all_component_ids_present(self, bom_text, scout):
        for comp_id in scout.components:
            assert comp_id in bom_text, f"Component {comp_id} missing from BOM"

    def test_components_section(self, bom_text):
        assert "## Components" in bom_text

    def test_wire_section(self, bom_text):
        assert "## Wire" in bom_text
        assert "AWG" in bom_text

    def test_main_wire_gauges_present(self, bom_text):
        assert "10 AWG" in bom_text
        assert "18 AWG" in bom_text
        assert "26 AWG" in bom_text

    def test_connectors_section(self, bom_text):
        assert "## Connectors" in bom_text
        assert "JST-PH-4" in bom_text

    def test_bom_overrides_section(self, bom_text):
        assert "## Additional hardware" in bom_text
        assert "4.7kΩ" in bom_text
        assert "Heat shrink" in bom_text

    def test_wire_lengths_tbd_flagged(self, bom_text):
        assert "TBD" in bom_text

    def test_known_lengths_show_waste(self, bom_text):
        # 10AWG runs have lengths, should show cut waste notice
        assert "cut waste" in bom_text
