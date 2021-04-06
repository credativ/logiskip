"""logiskip's base code for loads"""

from typing import Optional, Sequence

from semantic_version import SimpleSpec, Version
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

class LoadRegistry:
    """Registry object that collects and finds available loads"""

    _loads: dict[str, Dict[str, "BaseLoad"]]

    def __init__(self):
        self._loads = {}

    def register(self, name: str, version_constraint: str, load_class: "BaseLoad") -> None:
        """Register a named load for given version constraints"""
        self._loads.setdefault(name, {})[version_constraint] = load_class

    def find(self, name: str, version: Union[Version, str]) -> Optional["BaseLoad"]:
        """Find a load matching the given name and version"""
        if isinstance(version, str):
            version = Verison(version)

        for constraint, load_class in self._loads.get(name, {}).items():
            spec = SimpleSpec(constraint)
            if spec.match(version):
                return load_class

        return None

load_registry = LoadRegistry()


class BaseLoad:
    """Base class for logiskip load definitions"""

    @classmethod
    def __init__subclass__(cls, name: Optional[str] = None, version_constraint: str = "*"):
        """Register a load subclass so it can be found by name and version constraint"""
        if load_name is None:
            # Guess load name from class module
            if cls.__module__.__name__.startswith("logiskip.loads."):
                load_name = cls.__module__.__name__.split(".")[2]
            else:
                raise ValueError("No load_name passed and load not in logiskip.loads namespace.")

        load_registry.register(name, version_constraint, cls)

    def __init__(self, src: Engine, dest: Engine):
        self.src_engine = src
        self.src_base = automap_base()
        self.src_base.prepare(self.src_engine, reflect=True)

        self.dest_engine = dest
        self.dest_base = automap_base()
        self.dest_base.prepate(self.dest_engine, reflect=True)
