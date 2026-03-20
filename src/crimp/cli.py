"""Crimp CLI entry point."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from crimp import __version__
from crimp.manifest import ManifestError, load

console = Console()


@click.group()
@click.version_option(__version__)
def cli():
    """Crimp — AI-native hardware manifest tool for makers and robot builders.

    The AI writes the manifest. You follow the generated assembly guide.
    """


@cli.command()
@click.argument("manifest", type=click.Path(exists=True))
@click.option("--output", "-o", default="crimp-output", help="Output directory.")
@click.option("--dry-run", is_flag=True, help="List outputs without writing files.")
def build(manifest, output, dry_run):
    """Generate all outputs from a manifest file."""
    try:
        m = load(manifest)
    except ManifestError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    output_dir = Path(output)
    console.print(f"[green]✓[/green] Manifest valid: [bold]{m.project.name}[/bold] (crimp {m.crimp_version})")
    console.print(f"  {len(m.components)} components, {len(m.connections)} connections")
    console.print()

    from crimp.generators import assembly as assembly_gen
    from crimp.generators import bom as bom_gen
    from crimp.generators import commissioning as comm_gen
    from crimp.generators import pinout as pinout_gen

    tested = sum(1 for c in m.connections if c.commissioning.test_method != "none")

    if dry_run:
        console.print("[dim]dry-run: would write:[/dim]")
        console.print(f"  pinout/index.md + {len(m.components)} component files → {output_dir}/pinout/")
        console.print(f"  assembly-guide.md ({len(m.connections)} steps) → {output_dir}/")
        console.print(f"  bom.md ({len(m.components)} components) → {output_dir}/")
        console.print(f"  commissioning_tests.py ({tested} tests) → {output_dir}/")
    else:
        written = pinout_gen.generate(m, output_dir)
        console.print(f"[green]✓[/green] Pinout docs: {len(written)} files → [bold]{output_dir}/pinout/[/bold]")

        guide = assembly_gen.generate(m, output_dir)
        console.print(f"[green]✓[/green] Assembly guide: {len(m.connections)} steps → [bold]{guide}[/bold]")

        bom = bom_gen.generate(m, output_dir)
        console.print(f"[green]✓[/green] BOM: {len(m.components)} components → [bold]{bom}[/bold]")

        comm = comm_gen.generate(m, output_dir)
        console.print(f"[green]✓[/green] Commissioning tests: {tested} tests → [bold]{comm}[/bold]")

        try:
            from crimp.generators import wireviz_gen
            diagrams = wireviz_gen.generate(m, output_dir)
            svg_count = sum(1 for p in diagrams if p.suffix == ".svg")
            console.print(f"[green]✓[/green] Wiring diagrams: {svg_count} SVGs → [bold]{output_dir}/diagrams/[/bold]")
        except RuntimeError:
            console.print("[dim]  (wiring diagrams skipped — wireviz not installed)[/dim]")


@cli.command()
@click.argument("manifest", type=click.Path(exists=True))
def validate(manifest):
    """Validate a manifest file against the Crimp schema."""
    try:
        m = load(manifest)
    except ManifestError as e:
        console.print(f"[red]✗ Invalid:[/red] {e}")
        raise SystemExit(1)

    console.print(f"[green]✓ Valid:[/green] [bold]{m.project.name}[/bold]")
    console.print(f"  crimp_version : {m.crimp_version}")
    console.print(f"  components    : {len(m.components)}")
    console.print(f"  connections   : {len(m.connections)}")
    console.print(f"  wire_standards: {len(m.wire_standards)}")
    console.print(f"  power_rails   : {len(m.power_rails)}")

    if m.components:
        table = Table(title="Components", show_lines=False)
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Pins")
        for comp_id, comp in m.components.items():
            table.add_row(comp_id, comp.name, comp.type, str(len(comp.pins)))
        console.print(table)


@cli.command()
@click.argument("manifest", type=click.Path(exists=True))
@click.option("--host", default="0.0.0.0", help="Host to bind (default: all interfaces).")
@click.option("--port", default=8000, help="Port to listen on (default: 8000).")
def serve(manifest, host, port):
    """Run the interactive commissioning web UI.

    Loads MANIFEST and serves a guided step-by-step assembly checklist.
    Open http://<this-machine>:PORT in your browser to start commissioning.
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[red]Error:[/red] uvicorn not installed. Run: pip install 'crimp-manifest[serve]'")
        raise SystemExit(1)

    try:
        m = load(manifest)
    except ManifestError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    from crimp.server import create_app

    console.print(f"[green]✓[/green] Manifest: [bold]{m.project.name}[/bold] — {len(m.connections)} connections")
    console.print(f"[green]✓[/green] Serving at [bold]http://{host}:{port}[/bold]  (Ctrl-C to stop)")
    console.print()

    app = create_app(m)
    uvicorn.run(app, host=host, port=port, log_level="warning")


@cli.command()
def schema():
    """Print the Crimp manifest JSON schema (useful for prompting an AI)."""
    from crimp.manifest import SCHEMA_PATH
    console.print(json.dumps(json.loads(SCHEMA_PATH.read_text()), indent=2))
