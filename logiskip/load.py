"""logiskip's base code for loads"""

from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session


class BaseLoad:
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
