"""logiskip's base code for loads"""

from typing import Optional, Sequence

from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

class LoadRegistry:
    """Registry object that collects and finds available loads"""

    _loads: dict[str, Dict[str, "BaseLoad"]]

    def __init__(self):
        self._loads = {}

    def register(self, name: str, versions: Sequence[str], load_class: "BaseLoad") -> None:
        """Register a named load for given versions"""
        self._loads.setdefault(name, {}).update({version: load_class for version in versions})

load_registry = LoadRegistry()


class BaseLoad:
    """Base class for logiskip load definitions"""

    @classmethod
    def __init__subclass__(cls, load_name: Optional[str] = None, load_versions: Optional[Sequence[str]] = None):
        """Register a load subclass so it can be found by name and version"""
        if load_name is None:
            # Guess load name from class module
            if cls.__module__.__name__.startswith("logiskip.loads."):
                load_name = cls.__module__.__name__.split(".")[2]
            else:
                raise ValueError("No load_name passed and load not in logiskip.loads namespace.")

        if load_versions is None:
            # Default to all versions
            load_versions = [">0"]

        load_registry.register(load_name, load_versions, cls)

    def __init__(self, src: Engine, dest: Engine):
        self.src_engine = src
        self.src_base = automap_base()
        self.src_base.prepare(self.src_engine, reflect=True)

        self.dest_engine = dest
        self.dest_base = automap_base()
        self.dest_base.prepate(self.dest_engine, reflect=True)

    @staticmethod
    def find_load(name: str, version: str) -> "BaseLoad":
        pass
