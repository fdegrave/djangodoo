=========
Djangodoo
=========

Djangodoo allows you to copy models from Odoo to Django, load records from Odoo as well as modifying them. It also provides an authentication  mechanism using the Odoo authentication. This app makes a wide use of the Erppeek library. 

Quick start
-----------

1. Add "Djangodoo" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        ...
        'Djangodoo',
    )

2. Include the Odoo host configuration in your project settings like this::

    ODOO_HOST = {
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST': 'http://localhost',
        'PORT': 8069,
        'DB': 'dbname'
    }

3. [optional] Include the Odoo authentication backend in your project settings like this::

    AUTHENTICATION_BACKENDS = ('djangodoo.auth.OdooAuthBackend')

4. Define a model like this::

    from djangodoo.models import OdooModel
    
    class Partner(OdooModel):
        _odoo_model = "res.partner"
        _odoo_fields = ['name']  # optional; if omitted, all fields are copied
        _odoo_ignore_fields = None  # optional; fields in this list are not copied
