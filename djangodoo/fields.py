# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models as djangomodels
from django.utils import translation
from django.utils.functional import lazy
from django.utils import six
import base64

"""
    Translation methods
"""


def _get_details_in_lang(field, lang):
    if field.translation_cache.get(lang):
        return field.translation_cache[lang]
    else:
        settings.odoo_models[field.details['model']].cache_translation(lang)
        try:
            return field.translation_cache[lang]
        except:
            return field.details


def field_translate(field, key):
    lang = translation.get_language() or "en-us"
    details = _get_details_in_lang(field, lang)
    res = details.get(key, "")
    if isinstance(res, six.binary_type):
        res = six.text_type(res)
    return res

_ = lazy(field_translate, six.text_type)


def selection_translate(field):
    def trans(val):
        lang = translation.get_language() or "en-us"
        details = _get_details_in_lang(field, lang)
        return dict(details['selection'])[val]

    trans_lazy = lazy(trans, six.text_type)

    res = []
    for val, _label in field.details.get('selection'):
        res.append((val, trans_lazy(val)))
    return tuple(res)


# TODO: default values
# TODO: domains

FIELDS_CONV = {
    "char": "CharField",
    "boolean": "BooleanField",
    "integer": "IntegerField",
    "text": "TextField",
    "float": "DecimalField",
    "date": "DateField",
    "datetime": "DateTimeField",
    "time": "TimeField",
    "binary": "BinaryField",
    "selection": "CharField",
    "many2one": "ForeignKey",
    "one2many": None,
    #     "many2many": "",
    #     "function": "",
    #     "related": "",
}


class OdooField(object):

    def __init__(self, details):
        self.details = details
        self.translatable = details.get("translate")
        self.django_field = False
        self.translation_cache = {}  # translations cache
        return super(OdooField, self).__init__()

    def to_django(self, **kwargs):
        kwargs.update({
            "verbose_name": _(self, 'string'),
            "help_text": _(self, 'help'),
            "blank": not(self.details.get("required")),
            "editable": not(self.details.get("readonly")),
        })
        django_field = getattr(djangomodels, FIELDS_CONV[self.details["type"]])(**kwargs)
        django_field.odoo_field = self
        self.django_field = django_field
        return django_field

    def convert_data(self, data):
        return data or None

    def convert_back(self, data):
        return data or False


class TextField(OdooField):

    def to_django(self, **kwargs):
        if self.details.get("required"):
            kwargs["default"] = ""
        kwargs["null"] = not(self.details.get("required"))
        return super(TextField, self).to_django(**kwargs)


class CharField(TextField):

    def to_django(self, **kwargs):
        kwargs['max_length'] = self.details.get('size') or 512
        return super(CharField, self).to_django(**kwargs)


class BooleanField(OdooField):

    def to_django(self, **kwargs):
        kwargs["default"] = False
        return super(BooleanField, self).to_django(**kwargs)

    def convert_data(self, data):
        return data or False


class IntegerField(OdooField):

    def to_django(self, **kwargs):
        if self.details.get("required"):
            kwargs["default"] = 0
        kwargs["null"] = not(self.details.get("required"))
        return super(IntegerField, self).to_django(**kwargs)


class FloatField(IntegerField):

    def to_django(self, **kwargs):
        if self.details.get("digits"):
            kwargs["max_digits"] = self.details["digits"][0]
            kwargs["decimal_places"] = self.details["digits"][1]
        kwargs["null"] = not(self.details.get("required"))
        return super(FloatField, self).to_django(**kwargs)


class DateField(OdooField):

    def to_django(self, **kwargs):
        kwargs["null"] = not(self.details.get("required"))
        if self.details.get("required"):
            kwargs["auto_now_add"] = True
        return super(DateField, self).to_django(**kwargs)


class DateTimeField(DateField):
    pass


class TimeField(DateField):
    pass


class BinaryField(OdooField):

    def to_django(self, **kwargs):
        kwargs["null"] = not(self.details.get("required"))
        return super(BinaryField, self).to_django(**kwargs)

    def convert_data(self, data):
        """Odoo data is a b64-encoded string"""
        return base64.b64decode(data) if data else None

    def convert_back(self, data):
        return base64.b64encode(data).decode("utf-8") if data else False


class SelectionField(CharField):

    def to_django(self, **kwargs):
        kwargs["choices"] = selection_translate(self)
        return super(SelectionField, self).to_django(**kwargs)


class Many2OneField(OdooField):

    """
        If the model identified by details['relation'] exists in django, then we can create the field directly.
        Otherwise, we delay the field creation until the possible creation of this model.
    """

    def __new__(cls, details):
        if details['relation'] in settings.odoo_models:
            return OdooField.__new__(cls)
        else:
            settings.deferred_m2o[details['relation']] = settings.deferred_m2o.get(details['relation'], [])
            settings.deferred_m2o[details['relation']].append(details)
            return None

    def to_django(self, **kwargs):
        kwargs["null"] = not(self.details.get("required"))
        if self.details['relation'] == self.details['model']:
            kwargs["to"] = "self"
        else:
            to_model = settings.odoo_models[self.details['relation']]
            kwargs["to"] = to_model
        return super(Many2OneField, self).to_django(**kwargs)

    def convert_data(self, data):
        """
            Odoo data is a pair (id, label)
            We look for objects in the target model an instance having a odoo_id equal to the first
            element of the pair ; if not found, we load it from Odoo

            :param (tuple or False) data: the value to convert
            :return (OdooModel or False): the object instance linked to this m2o field
        """
        if data and isinstance(data, (list, tuple)) and len(data) == 2:
            to_model = settings.odoo_models[self.details['relation']]
            targets = to_model.objects.filter(odoo_id=data[0])
            if targets:
                return targets[0]
            else:
                return to_model.odoo_load([data[0]])[0]
        return data or None

    def convert_back(self, data):
        """
            Django data is either None or a Django instance
            We tranform it into False or an integer by getting the odoo_id on the instance.

            :todo: if the target objet has no odoo_id, first push it to odoo
            :param (OdooModel or False) data: the value to convert
            :return (integer or False): the idi of the object in odoo
        """
        from .models import OdooModel
        if data and isinstance(data, OdooModel) and hasattr(data, 'odoo_id'):
            return data.odoo_id
#         elif isinstance(data, (int, long)):
#             return data
        else:
            return False


class One2ManyField(OdooField):

    """
        There is no one2many field in Django, so we simply set the "relation_field"
        attribute of the foreignKey field encoding the opposite relationship so it bares
        the name of this one2many field
    """
    def __new__(cls, details):
        if details['relation'] in settings.odoo_models:
            relation = settings.odoo_models[details['relation']]
            for field in relation._meta.Fields:
                if field.name == details['relation_field']:
                    field.related_name = details['name']
        else:
            settings.deferred_o2m[details['relation']] = settings.deferred_o2m.get(details['relation'], [])
            settings.deferred_o2m[details['relation']].append(details)


def convert_field(details):
    if not(details['type'] in FIELDS_CONV):
        return None
    return eval(details["type"].title() + "Field")(details)
