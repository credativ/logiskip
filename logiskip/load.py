"""logiskip's base code for loads"""

from typing import Optional, Sequence, Union

from semantic_version import SimpleSpec, Version
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

    def __init_subclass__(cls, /, name: Optional[str] = None, version_constraint: str = "*", **kwargs):
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
        table_map = getattr(self, "table_map_{self.src_dialect}_{self.dest_dialect}", {})
        return table_map.get(src_table_name, src_table_name)

    def run(self) -> None:
        """Run the migration defined by this load"""
        # Determine SQL dialects used by source and destination
        src_dialect = self.src_engine.dialect.name
        dest_dialect = self.dest_engine.dialect.name

        # Handle all known tables in order
        for src_table_name, src_table in self.src_base.metadata.tables.items():
            # Determine destination table name
            dest_table_name = self.get_dest_table_name(src_table_name)
            if dest_table_name is None:
                # If dest_table is explicitly None, skip the table
                continue
            dest_table = self.dest_base.metadata.tables[dest_table_name]
            print(src_table, dest_table)
