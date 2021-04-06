"""logiskip's command-line interface"""

import logging

import click
import click_logging

from .load import load_registry

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
_logger = logging.getLogger("logiskip")


@click.command()
@click.option("--source", prompt="Source URI", help="URI of source database")
@click.option("--destination", prompt="Destination URI", help="URI of destination database")
@click.option(
    "--load-name", prompt="Load name", help="Name of load plugin for migrated application"
)
@click.option(
    "--load-version", prompt="Load version", help="Version of migrated application/schema"
)
@click.option(
    "--dry-run", help="Roll back transaction instead of commiting", is_flag=True, default=False
)
@click_logging.simple_verbosity_option(_logger)
def logiskip(
    source: str, destination: str, load_name: str, load_version: str, dry_run: bool
) -> None:
    """Main executable for logiskip"""
    load_class = load_registry.find(load_name, load_version)
    load = load_class(source, destination)
    load.migrate(commit=not dry_run)
