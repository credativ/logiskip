"""logiskip's main migration logic"""

from typing import Union

from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine

from .load import BaseLoad, load_registry


class Migrator:
    def __init__(self, src: Union[Engine, str], dest: Union[Engine, str], load: Union[BaseLoad, tuple[str, str]]):
        if isinstance(src, str):
            self.source_engine = create_engine(src)
        else:
            self.source_engine = src

        if isinstance(dest, str):
            self.dest_engine = create_engine(dest)
        else:
            self.dest_engine = dest

        if isinstance(load, tuple):
            load = load_registry.find(load[0], load[1])
        self.load = load(self.source_engine, self.dest_engine)

    def run(self) -> None:
        pass
