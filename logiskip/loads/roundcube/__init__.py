"""logiskip load definition for Roundcube"""

from logiskip.load import BaseLoad


class RoundcubeLoad(BaseLoad, load_name="roundcube", load_versions=["1.4.1"]):
    pass
