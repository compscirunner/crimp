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
    from crimp.generators import pinout as pinout_gen

    if dry_run:
        console.print("[dim]dry-run: would write:[/dim]")
        console.print(f"  pinout/index.md + {len(m.components)} component files → {output_dir}/pinout/")
        console.print(f"  assembly-guide.md ({len(m.connections)} steps) → {output_dir}/")
    else:
        written = pinout_gen.generate(m, output_dir)
        console.print(f"[green]✓[/green] Pinout docs: {len(written)} files → [bold]{output_dir}/pinout/[/bold]")

        guide = assembly_gen.generate(m, output_dir)
        console.print(f"[green]✓[/green] Assembly guide: {len(m.connections)} steps → [bold]{guide}[/bold]")


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
def schema():
    """Print the Crimp manifest JSON schema (useful for prompting an AI)."""
    from crimp.manifest import SCHEMA_PATH
    console.print(json.dumps(json.loads(SCHEMA_PATH.read_text()), indent=2))
