"""Tests for the pinout markdown generator."""

from pathlib import Path

import pytest

from crimp.manifest import load
from crimp.generators import pinout as pinout_gen

SCOUT = Path(__file__).parent.parent / "examples" / "scout-robot" / "manifest.json"


@pytest.fixture(scope="module")
def scout():
    return load(SCOUT)


@pytest.fixture(scope="module")
def output(tmp_path_factory, scout):
    out = tmp_path_factory.mktemp("pinout")
    pinout_gen.generate(scout, out)
    return out / "pinout"


class TestPinoutOutput:
    def test_index_created(self, output):
        assert (output / "index.md").exists()

    def test_one_file_per_component(self, output, scout):
        for comp_id in scout.components:
            assert (output / f"{comp_id}.md").exists(), f"Missing {comp_id}.md"

    def test_file_count(self, output, scout):
        md_files = list(output.glob("*.md"))
        # index + one per component
        assert len(md_files) == len(scout.components) + 1

    def test_index_contains_all_component_ids(self, output, scout):
        index = (output / "index.md").read_text()
        for comp_id in scout.components:
            assert comp_id in index, f"{comp_id} not in index"

    def test_index_contains_power_rails(self, output, scout):
        index = (output / "index.md").read_text()
        for rail_id in scout.power_rails:
            assert rail_id in index

    def test_pico_page_has_all_pins(self, output, scout):
        pico_md = (output / "pico.md").read_text()
        for pin_id in scout.components["pico"].pins:
            assert pin_id in pico_md, f"Pin {pin_id} missing from pico.md"

    def test_pico_page_shows_connections(self, output):
        pico_md = (output / "pico.md").read_text()
        assert "as5600_left" in pico_md
        assert "enc_left_sda" in pico_md

    def test_pico_page_shows_rail(self, output):
        pico_md = (output / "pico.md").read_text()
        assert "5v_logic" in pico_md
