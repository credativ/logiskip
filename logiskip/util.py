"""Utility code for logiskip"""

default_drivers = {
    "mysql": "pymysql",
    "postgresql": "pg8000",
    "sqlite": "pysqlite",
    "oracle": "cx_oracle",
    "mssql": "pymssql",
}


def add_default_driver(uri: str) -> str:
    """Add the preferred dialect to an SQLAlchemy URI"""
    parts = uri.split("://", 1)
    if "+" in parts[0]:
        return uri
    else:
        driver = default_drivers.get(parts[0], None)
        if driver:
            parts[0] += f"+{driver}"
    return "://".join(parts)
