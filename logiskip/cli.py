"""logiskip's command-line interface"""

import click

from .migrator import Migrator


@click.command()
@click.option("--source", prompt="Source URI", help="URI of source database")
@click.option("--destination", prompt="Destination URI", help="URI of destination database")
@click.option("--load", prompt="Load name", help="Name of load plugin for migrated application")
@click.option("--version", prompt="Load version", help="Version of migrated application/schema")
def logiskip(source: str, destination: str, load: str, version: str) -> None:
    """Main executable for logiskip"""
    migrator = Migrator(source, destination, (load, version))
    migrator.run()
