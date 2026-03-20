"""Crimp CLI entry point."""

import click
from crimp import __version__


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
    click.echo("build: not yet implemented")


@cli.command()
@click.argument("manifest", type=click.Path(exists=True))
def validate(manifest):
    """Validate a manifest file against the Crimp schema."""
    click.echo("validate: not yet implemented")


@cli.command()
def schema():
    """Print the Crimp manifest JSON schema (useful for prompting an AI)."""
    import json
    from pathlib import Path
    schema_path = Path(__file__).parent.parent.parent / "schema" / "manifest.schema.json"
    click.echo(json.dumps(json.loads(schema_path.read_text()), indent=2))
