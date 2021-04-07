"""logiskip's base code for loads"""

import logging
import sys
from typing import Any, Optional, Sequence, Union

from semantic_version import SimpleSpec, Version
from sqlalchemy import Table, create_engine, insert, select
from sqlalchemy.engine import Connection
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.automap import automap_base

if sys.version_info >= (3, 9):
    from importlib import metadata
else:
    import importlib_metadata as metadata

from .util import add_default_driver

_logger = logging.getLogger("logiskip")


class LoadRegistry:
    """Registry object that collects and finds available loads"""

    _loads: dict[str, dict[str, "BaseLoad"]]

    @staticmethod
    def import_known_loads() -> None:
        for ep in metadata.entry_points().get("logiskip.load", []):
            __import__(ep.module)
            _logger.debug("Found load %s", ep.module)

    def __init__(self):
        self._loads = {}

    def register(self, name: str, version_constraint: str, load_class: "BaseLoad") -> None:
        """Register a named load for given version constraints"""
        self._loads.setdefault(name, {})[version_constraint] = load_class
        _logger.debug("Registered load %s for versions %s", name, version_constraint)

    def find(self, name: str, version: Union[Version, str]) -> Optional["BaseLoad"]:
        """Find a load matching the given name and version"""
        if isinstance(version, str):
            version = Version(version)

        for constraint, load_class in self._loads.get(name, {}).items():
            spec = SimpleSpec(constraint)
            if spec.match(version):
                _logger.debug(
                    "Found load %s for versions %s, matching %s", name, constraint, version
                )
                return load_class

        _logger.error("No load %s found for version %s", name, version)
        return None


class BaseLoad:
    """Base class for logiskip load definitions"""

    @property
    def src_dialect(self) -> str:
        """Dialect name of source"""
        return self.src_engine.dialect.name

    @property
    def dest_dialect(self) -> str:
        """Dialect name of destination"""
        return self.dest_engine.dialect.name

    def __init_subclass__(
        cls, /, name: Optional[str] = None, version_constraint: str = "*", **kwargs
    ):
        """Register a load subclass so it can be found by name and version constraint"""
        super().__init_subclass__(**kwargs)

        if name is None:
            # Guess load name from class module
            if cls.__module__.startswith("logiskip.loads."):
                name = cls.__module__.split(".")[2]
            else:
                raise TypeError("No load name passed and load not in logiskip.loads namespace.")

        # Store information on class for later use
        cls.name = name
        cls.version_constraint = version_constraint

        load_registry.register(name, version_constraint, cls)

    def __init__(self, src: Union[Engine, str], dest: Union[Engine, str]):
        if isinstance(src, str):
            src = add_default_driver(src)
            self.src_engine = create_engine(src)
        else:
            self.src_engine = src
        self.src_base = automap_base()
        _logger.info("Discovering DDL for source (%s)", self.src_dialect)
        self.src_base.prepare(self.src_engine, reflect=True)

        if isinstance(dest, str):
            dest = add_default_driver(dest)
            self.dest_engine = create_engine(dest)
        else:
            self.dest_engine = dest
        self.dest_base = automap_base()
        _logger.info("Discovering DDL for destination (%s)", self.dest_dialect)
        self.dest_base.prepare(self.dest_engine, reflect=True)

    def get_dest_table_name(self, src_table_name: str) -> str:
        """Determine destination table name"""
        table_map = getattr(
            self,
            f"{self.src_dialect}_{self.dest_dialect}_tables",
            getattr(self, "default_tables", {}),
        )
        return table_map.get(src_table_name, src_table_name)

    def get_dest_field(self, src_table: Table, src_field: str) -> str:
        """Determine the destination field name"""
        field_map = getattr(
            self,
            f"{self.src_dialect}_{self.dest_dialect}_fields_{src_table.name}",
            getattr(self, f"default_fields_{src_table.name}", {}),
        )
        return field_map.get(src_field, src_field)

    def convert_table(self, src_table: Table) -> None:
        """Convert one table from source to destination"""
        _logger.info("Converting table %s", src_table.name)

        # Determine destination table
        dest_table_name = self.get_dest_table_name(src_table.name)
        if dest_table_name is None:
            # If dest_table_name is explicitly None, skip the table
            _logger.info("Skipping table %s (explicitly disabled)", src_table.name)
            return None
        _logger.debug("Table %s mapped to %s", src_table.name, dest_table_name)
        dest_table = self.dest_base.metadata.tables[dest_table_name]

        # Look for an explicit conversion method; resort to default implementation
        convert_meth = getattr(
            self,
            f"{self.src_dialect}_{self.dest_dialect}_table_{src_table.name}",
            getattr(self, f"default_table_{src_table.name}", self._convert_table_default),
        )
        return convert_meth(src_table, dest_table)

    def _convert_table_default(self, src_table: Table, dest_table: Table) -> None:
        # Extract all source rows
        src_stmt = src_table.select()
        dest_rows = []
        with self.src_engine.connect() as src_conn:
            for src_row in src_conn.execute(src_stmt):
                # Convert to destination row
                dest_row = self.convert_row(src_table, src_row._asdict())
                dest_rows.append(dest_row)

        if dest_rows:
            return dest_table.insert().values(dest_rows)
        return None

    def convert_row(self, src_table: Table, src_dict: dict[str, Any]) -> dict[str, Any]:
        """Convert a single row from a single table"""
        _logger.debug("Converting row %s", str(src_dict.values()))

        # Look for an explicit conversion method; resort to default implementation
        convert_meth = getattr(
            self,
            f"{self.src_dialect}_{self.dest_dialect}_row_{src_table.name}",
            getattr(self, f"default_row_{src_table.name}", self._convert_row_default),
        )
        return convert_meth(src_table, src_dict)

    def _convert_row_default(self, src_table: Table, src_dict: dict[str, Any]) -> dict[str, Any]:
        dest_dict = {}
        # Convert every single field
        for src_field, src_value in src_dict.items():
            # Determine destination field name
            dest_field = self.get_dest_field(src_table, src_field)
            if dest_field is None:
                # Skip field if explicitly set to None
                continue

            # Look for an explicit conversion method; resort to default implementation
            convert_meth = getattr(
                self,
                f"{self.src_dialect}_{self.dest_dialect}_field_{src_table.name}__{src_field}",
                getattr(
                    self,
                    f"default_field_{src_table.name}__{src_field}",
                    self._convert_field_default,
                ),
            )
            dest_value = convert_meth(src_value)

            dest_dict[dest_field] = dest_value

        return dest_dict

    def _convert_field_default(self, src_value: Any) -> Any:
        return src_value

    def migrate(self, commit: bool = True) -> None:
        """Run the migration defined by this load"""
        _logger.info("Migrating %s from %s to %s", self.name, self.src_dialect, self.dest_dialect)
        # Handle all known tables in order
        with self.dest_engine.connect() as dest_conn:
            with dest_conn.begin() as transaction:
                for src_table in self.src_base.metadata.tables.values():
                    dest_stmt = self.convert_table(src_table)
                    if dest_stmt is None:
                        # Skip if result is empty
                        continue
                    dest_conn.execute(dest_stmt)

                # Roll-back if commit is not desired
                if commit:
                    _logger.info(
                        "Migrated %s from %s to %s", self.name, self.src_dialect, self.dest_dialect
                    )
                else:
                    transaction.rollback()
                    _logger.warning("Transaction rolled back (explicitly requested)")


load_registry = LoadRegistry()
LoadRegistry.import_known_loads()
