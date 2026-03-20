"""Tests for the WireViz diagram generator."""

from pathlib import Path

import pytest

from crimp.manifest import load
from crimp.generators import wireviz_gen

SCOUT = Path(__file__).parent.parent / "examples" / "scout-robot" / "manifest.json"


@pytest.fixture(scope="module")
def scout():
    return load(SCOUT)


@pytest.fixture(scope="module")
def diagrams_dir(tmp_path_factory, scout):
    out = tmp_path_factory.mktemp("wv")
    wireviz_gen.generate(scout, out)
    return out / "diagrams"


class TestWireVizGenerator:
    def test_diagrams_dir_created(self, diagrams_dir):
        assert diagrams_dir.exists()

    def test_index_md_created(self, diagrams_dir):
        assert (diagrams_dir / "index.md").exists()

    def test_svgs_generated(self, diagrams_dir):
        svgs = list(diagrams_dir.glob("*.svg"))
        assert len(svgs) > 0, "No SVG files generated"

    def test_relay_phase_diagram_exists(self, diagrams_dir):
        # Phase 3 (relay board) is small enough — should always produce a diagram
        svgs = list(diagrams_dir.glob("*relay*"))
        assert len(svgs) > 0, "Expected relay board diagram"

    def test_svgs_are_valid_xml(self, diagrams_dir):
        import xml.etree.ElementTree as ET
        for svg in diagrams_dir.glob("*.svg"):
            try:
                ET.parse(svg)
            except ET.ParseError as e:
                pytest.fail(f"{svg.name} is not valid XML: {e}")

    def test_svgs_are_nonzero(self, diagrams_dir):
        for svg in diagrams_dir.glob("*.svg"):
            assert svg.stat().st_size > 1000, f"{svg.name} is suspiciously small"

    def test_index_lists_diagrams(self, diagrams_dir):
        index = (diagrams_dir / "index.md").read_text()
        for svg in diagrams_dir.glob("*.svg"):
            assert svg.name in index, f"{svg.name} not listed in index.md"
