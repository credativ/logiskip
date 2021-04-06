"""logiskip's command-line interface"""

import click

from .load import load_registry


@click.command()
@click.option("--source", prompt="Source URI", help="URI of source database")
@click.option("--destination", prompt="Destination URI", help="URI of destination database")
@click.option("--load-name", prompt="Load name", help="Name of load plugin for migrated application")
@click.option("--load-version", prompt="Load version", help="Version of migrated application/schema")
def logiskip(source: str, destination: str, load_name: str, load_version: str) -> None:
    """Main executable for logiskip"""
    load_class = load_registry.find(load_name, load_version)
    load = load_class(source, destination)
    load.migrate()
