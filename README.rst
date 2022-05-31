modoboa-admin
=============

|travis| |codecov| |landscape|

The administration panel of Modoboa.

Installation
------------

Install this extension system-wide or inside a virtual environment by
running the following command::

  $ pip install modoboa-admin

Edit the settings.py file of your modoboa instance and add
``modoboa_admin`` inside the ``MODOBOA_APPS`` variable like this::

    MODOBOA_APPS = (
      'modoboa',
      'modoboa.core',
      'modoboa.lib',
    
      # Extensions here
      'modoboa_admin',
    )

Run the following commands to setup the database tables::

  $ cd <modoboa_instance_dir>
  $ python manage.py migrate modoboa_admin
  $ python manage.py load_initial_data
    
Finally, restart the python process running modoboa (uwsgi, gunicorn,
apache, whatever).

.. |landscape| image:: https://landscape.io/github/modoboa/modoboa-admin/master/landscape.svg?style=flat
   :target: https://landscape.io/github/modoboa/modoboa-admin/master
   :alt: Code Health
.. |travis| image:: https://travis-ci.org/modoboa/modoboa-admin.png?branch=master
   :target: https://travis-ci.org/modoboa/modoboa-admin
.. |codecov| image:: http://codecov.io/github/modoboa/modoboa-admin/coverage.svg?branch=master
   :target: http://codecov.io/github/modoboa/modoboa-admin?branch=master
