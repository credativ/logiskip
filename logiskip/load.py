"""logiskip's base code for loads"""

from typing import Any, Optional, Sequence, Union

from semantic_version import SimpleSpec, Version
from sqlalchemy import Table, insert, select
from sqlalchemy.engine import Connection
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.automap import automap_base


class LoadRegistry:
    """Registry object that collects and finds available loads"""

    _loads: dict[str, dict[str, "BaseLoad"]]

    def __init__(self):
        self._loads = {}

    def register(self, name: str, version_constraint: str, load_class: "BaseLoad") -> None:
        """Register a named load for given version constraints"""
        self._loads.setdefault(name, {})[version_constraint] = load_class

    def find(self, name: str, version: Union[Version, str]) -> Optional["BaseLoad"]:
        """Find a load matching the given name and version"""
        if isinstance(version, str):
            version = Version(version)

        for constraint, load_class in self._loads.get(name, {}).items():
            spec = SimpleSpec(constraint)
            if spec.match(version):
                return load_class

        return None


load_registry = LoadRegistry()


class BaseLoad:
    """Base class for logiskip load definitions"""

    table_map: dict[str, Optional[str]]

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

        load_registry.register(name, version_constraint, cls)

    def __init__(self, src: Engine, dest: Engine):
        self.src_engine = src
        self.src_base = automap_base()
        self.src_base.prepare(self.src_engine, reflect=True)

        self.dest_engine = dest
        self.dest_base = automap_base()
        self.dest_base.prepare(self.dest_engine, reflect=True)

    def get_dest_table_name(self, src_table_name: str) -> str:
        """Determine destination table name"""
        table_map = getattr(self, f"{self.src_dialect}_{self.dest_dialect}_tables", {})
        return table_map.get(src_table_name, src_table_name)

    def get_dest_field(self, src_table: Table, src_field: str) -> str:
        """Determine the destination field name"""
        field_map = getattr(
            self, f"{self.src_dialect}_{self.dest_dialect}_fields_{src_table.name}", {}
        )
        return field_map.get(src_field, src_field)

    def convert_table(self, src_table: Table) -> None:
        """Convert one table from source to destination"""
        # Determine destination table
        dest_table_name = self.get_dest_table_name(src_table.name)
        if dest_table_name is None:
            # If dest_table_name is explicitly None, skip the table
            return None
        dest_table = self.dest_base.metadata.tables[dest_table_name]

        # Look for an explicit conversion method; resort to default implementation
        convert_meth = getattr(
            self,
            f"{self.src_dialect}_{self.dest_dialect}_table_{src_table.name}",
            self._convert_table_default,
        )
        return convert_meth(src_table, dest_table)

    def _convert_table_default(self, src_table: Table, dest_table: Table) -> None:
        # Extract all source rows
        src_stmt = src_table.select()
        dest_rows = []
        with self.src_engine.connect() as src_conn:
            for src_row in src_conn.execute(src_stmt):
                # Convert to destinatoin row
                dest_row = self.convert_row(src_table, src_row._asdict())
                dest_rows.append(dest_row)

        if dest_rows:
            return dest_table.insert().values(dest_rows)
        return None

    def convert_row(self, src_table: Table, src_dict: dict[str, Any]) -> dict[str, Any]:
        """Convert a single row from a single table"""
        # Look for an explicit conversion method; resort to default implementation
        convert_meth = getattr(
            self,
            f"{self.src_dialect}_{self.dest_dialect}_row_{src_table.name}",
            self._convert_row_default,
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
                self._convert_field_default,
            )
            dest_value = convert_meth(src_value)

            dest_dict[dest_field] = dest_value

        return dest_dict

    def _convert_field_default(self, src_value: Any) -> Any:
        return src_value

    def run(self) -> None:
        """Run the migration defined by this load"""
        # Handle all known tables in order
        with self.dest_engine.begin() as dest_conn:
            for src_table in self.src_base.metadata.tables.values():
                dest_stmt = self.convert_table(src_table)
                if dest_stmt is None:
                    # Skip if result is empty
                    continue
                dest_conn.execute(dest_stmt)
