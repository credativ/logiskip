logiskip - Logical database migration between RDBMSs 
====================================================

Synopsis
--------

logiskip is a command-line tool written in Python (using `SQLAlchemy`_ that cam
migrate application data between different RDMSs, e.g. between MySQL and PostgreSQL.

It is modular, with the possibility to define migration logic for applications in
separate classes (so-called "loads").

logiskip can be used for simple tasks like mere copying of tables, but also for
more complex tasks (e.g. converting images to another format, converting complex
types, etc.).

Installation
------------

logiskip can be installed using `pip`. In doing so, the needed database engines
can be passed as extras. To install logiskip with the ability to convert between
MySQL and PostgreSQL::

  pip3 install 'logiskip[mysql,postgres]'

Usage
-----

The package installs the `logiskip` command, which takes the following options::

  --source TEXT        URI of source database
  --destination TEXT   URI of destination database
  --load-name TEXT     Name of load plugin for migrated application
  --load-version TEXT  Version of migrated application/schema
  --dry-run            Roll back transaction instead of commiting
  -v, --verbosity LVL  Either CRITICAL, ERROR, WARNING, INFO or DEBUG.
  --help               Show this message and exit.

The following example migrates an installation of `Roundcube`_ 1.4.1 from MySQL
to PostgreSQL::

  logiskip --source 'mysql://roundcube:secret@localhost/roundcube' \
           --destination 'postgresql://roundcube:secret@localhost/roundcube' \
	   --load-name roundcube --load-version 1.4.1

Loads
-----

Loads in logiskip define migrations for a single application within a version
constraint. Here is an artificial example:

.. code-block:: python

   from logiskip.load import BaseLoad
   from sqlalchemy.orm import sessionmaker

   class ExampleLoad(BaseLoad, name="example", version_constraint=">=1.0,<2.0"):
       """Load for the application example within the semver constraint 1.x"""

       # Table map for all migrations
       # Tables mapped to None are skipped
       default_tables = {
           "cache": None  # Do not migrate the cache table
       }

       # Table map for migrating from MySQL to PostgreSQL
       postgresql_mysql_tables = {
           "geolocations": None,  # Application supports GIS only in PostgreSQL
	   "user": "users"  # Historic naming issue
       }

       # Field map for the "user" table when migrating from PostgreSQL to MySQL
       postgresql_mysql_fields_user = {
           "geolocation_fk": None  # See above
       }

       def mysql_postgresql_row_users(self, src_table, src_dict):
           """Do reverse-geolocation for user addresses when migrating to PostgreSQL"""
	   # First, do the default conversion
	   dest_row = super()._convert_row_default(src_table, src_dict)

	   # Get geolocation for address
	   lat, lon = geocoder.reverse(dest_row["address"]

	   # Use SQLAlchemy to create a new geolocation entry
	   session = sessionmaker(bind=self.dest_engine)()
	   geoloc = self.dest_base.classes.geolocations(lat=lat, lon=lon)
	   session.commit()

	   # Set foreign key to geolocation
	   dest_row["geolocation_fk"] = geoloc.id
	   return dest_row

       # More examples include:
       #   x_y_field_tablename__fieldname(self, src_value) - Do a conversion on a single field value
       #   x_y_table_tablename - Do the full table conversion manually
       # x_y can be default in all places to be used for any migration pair


Credits
-------

logiskip was sponsored by:

* `credativ GmbH`_
* `Beuth Hochschule für Technik Berlin`_

::

   Copyright 2021 Dominik George <dominik.george@credativ.de>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

.. _SQLAlchemy: https://sqlalchemy.org/
.. _Roundcube: https://roundcube.net/
.. _credativ GmbH: https://credativ.de/
.. _Beuth Hochschule für Technik Berlin: https://www.beuth-hochschule.de/
