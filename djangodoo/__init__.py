# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.models.signals import class_prepared
import erppeek
from .fields import convert_field


def set_auth_cache():
    settings.CACHES = settings.CACHES or {}
    settings.CACHES["odoo_auth"] = {'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
                                    'LOCATION': '127.0.0.1:18069'}


def set_odoo_client():
    config = getattr(settings, "ODOO_HOST", False)
    try:
        settings.odoo = erppeek.Client("%s:%d" % (config['HOST'], config['PORT']), db=config['DB'],
                                       user=config['USER'], password=config['PASSWORD'], verbose=False)
        settings.odoo.context = {"lang": settings.LANGUAGE_CODE}
        settings.odoo_models = {}
        settings.deferred_m2o = {}
        settings.deferred_o2m = {}
    except ConnectionRefusedError:
        print("Unable to connect to a running Odoo server.")
        raise


def add_extra_model_fields(sender, **kwargs):
    """Dynamically add the fields by reading the fields of the original ODOO model

        The fields are "translated" by using the definitions in fields
    """
    def add_field(django_model, field_details):
        odoo_field = convert_field(field_details)
        if odoo_field:
            field = odoo_field.to_django()
            field.contribute_to_class(django_model, field_details['name'])

    odoo = settings.odoo
    if getattr(sender, "_odoo_model", False):
        settings.odoo_models[sender._odoo_model] = sender
        _all_fields = odoo.model(sender._odoo_model).fields(sender._get_odoo_fields())
        for fname, fdetails in _all_fields.items():
            fdetails['name'] = fname
            fdetails['model'] = sender._odoo_model
            add_field(sender, fdetails)

        if sender._odoo_model in settings.deferred_m2o:
            for m2o_details in settings.deferred_m2o[sender._odoo_model]:
                origin = settings.odoo_models[m2o_details['model']]
                add_field(origin, m2o_details)
            settings.deferred_m2o[sender._odoo_model] = []

set_auth_cache()
set_odoo_client()
class_prepared.connect(add_extra_model_fields, dispatch_uid="FQFEQ#rfq3r")
