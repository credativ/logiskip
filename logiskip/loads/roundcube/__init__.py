"""logiskip load definition for Roundcube"""

from logiskip.load import BaseLoad


class RoundcubeLoad(BaseLoad, name="roundcube", version_constraint=">=1.4,<1.6"):
    # The "system" table is pre-filled with the schema version
    default_tables = {"system": None}

    # The "dictionary" table has an "id" field in MySQL
    # Note from schema: redundant, for compat. with Galera Cluster
    # No other dialects have the field, so we can shorten it as default
    default_fields_dictionary = {"id": None}
