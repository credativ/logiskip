"""logiskip load definition for Roundcube"""

from logiskip.load import BaseLoad


class RoundcubeLoad(BaseLoad, name="roundcube", version_constraint="==1.4.1"):
    default_tables = {"system": None}
