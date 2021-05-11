"""default logiskip load definition"""

from logiskip.load import BaseLoad


class DefaultLoad(BaseLoad, name="default", version_constraint="*"):
    """Default Load for simple applications without constraint"""

