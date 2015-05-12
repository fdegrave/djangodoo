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


OdooModel
---------

*OdooModel* inherits from **django.db.models.Model**. You can thus do with an *OdooModel* anything you would do with a regular *django.db.models.Model*. However, *OdooModel* provides a number of additional features:

1. As stated in the "Quickstart" section, it allows you to provide the name of a model defined in Odoo as the value of the **_odoo_model** attribute. The fields of this latter model will be copied -- and "translated" -- into Django fields at runtime (and during the migration process, of course) (note that a *many2one* field from Odoo will be translated into a *ForeignKey* Django field only if the target model of this field is also copied into Django);


2. The **_odoo_fields** and **_odoo_ignore_fields** allow you to restrict the list of fields that are copied from the original Odoo model;

3. Several methods that ease the interactions with the Odoo server regarding the Odoo model under concern are provided:
    
    * odoo_load(*odoo_ids* [, *client*]): class method that loads records from Odoo, given their identifiers.
        * `odoo_ids` is a list of Odoo records identifiers (integers);
        * `client` is an instance of *erppeek.Client* that is used to load the data; if none is provided, the client is the one configured in the settings.

    * odoo_search(*domain*, *offset=0*, *limit=None*, *order=None*, *context=None* [, *client*]): class method that searches and loads records from Odoo, given a domain and a series of parameters for the *search* method in Odoo.
    
    * odoo_write(*objs*, *args* [, *client*]): class method that writes the values provided in `args` into the Odoo records originating the Django instances provided in `objs`.
    
    * odoo_push(*self*, *fieldnames=None* [, *client*]): method that saves a Django instance into Odoo. If the instance has an *odoo_id* then we call `write`, otherwise we call `create`; we only save the values of the fields indicated in `fieldnames`, or all of them if it is None.


.. Authentication
.. --------------


