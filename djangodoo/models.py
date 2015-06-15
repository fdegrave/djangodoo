# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.cache import caches
import erppeek

# TODO: traduction des DATA!!!
# TODO: lazy loading des objets many2one


class OdooModel(models.Model):

    """Model of a Odoo object copied in Django

        Attributes:
            _odoo_model: name of the Odoo model that will be copied in Django
            _odoo_fields: list of field names that will be copied from Odoo. If None, all field are copied.
            _odoo_ignore_fields: list of field names that will NOT be copied from Odoo
    """

    _odoo_model = None
    _odoo_fields = None
    _odoo_ignore_fields = None

    odoo_id = models.IntegerField(unique=True)

    def __init__(self, *args, **kwargs):
        self.translation_cache = {}
        return super(OdooModel, self).__init__(*args, **kwargs)

    class Meta:
        abstract = True

    @classmethod
    def _get_odoo_fields(cls):
        res = cls._odoo_fields or settings.odoo.model(cls._odoo_model).fields()
        return [f for f in res if not(f in (cls._odoo_ignore_fields or []))]

    @classmethod
    def odoo_load(cls, odoo_ids, client=None):
        """Loads records from Odoo

            Loads records from Odoo into Django instances given a list of Odoo identifiers *odoo_ids*.
            We read the data corresponding to the fields we need and convert it with respect
            to the type of field thanks to the methods defined in 'fields.py'. Each django field
            generated from a Odoo field contains a "odoo_field" attribute containing a "OdooField"
            instance.
        """
        def update_or_create(args):
            try:
                obj = cls.objects.get(odoo_id=args["odoo_id"])
                for (k, v) in args.items():
                    setattr(obj, k, v)
            except:
                obj = cls(**args)
                obj.save()
            return obj

        odoo_model = cls._odoo_model
        odoo_fields = cls._get_odoo_fields()
        client = client or settings.odoo
        records = client.model(odoo_model).read(odoo_ids, fields=odoo_fields, context=None)
        res = []
        for rec in records:
            args = {}
            args["odoo_id"] = rec["id"]
            del rec["id"]
            for field in cls._meta.fields:
                if hasattr(field, "odoo_field") and field.name in rec:
                    args[field.name] = field.odoo_field.convert_data(rec[field.name])

            res.append(update_or_create(args))
        return res

    @classmethod
    def odoo_search(cls, domain, offset=0, limit=None, order=None, context=None, client=None):
        """Search and load records from Odoo

            We load data from Odoo based on a domain filter
        """
        client = client or settings.odoo
        odoo_ids = client.search(cls._odoo_model, domain, offset=offset, limit=limit, order=order, context=context)
        return cls.odoo_load(odoo_ids, client=client) if odoo_ids else []

    @classmethod
    def odoo_write(cls, objs, args, client=None):
        """Writes in multiple records

            Writes the values provided in *args* into the Odoo records originating 
            the Django instances provided in *objs*
        """
        def convert(args):
            res = {}
            for field in cls._meta.fields:
                if field.name in args and hasattr(field, "odoo_field"):
                    res[field.name] = field.odoo_field.convert_back(args[field.name])
            return res

        client = client or settings.odoo
        odoo_model = cls._odoo_model
        odoo_ids = [o.odoo_id for o in objs if o.odoo_id]
        return client.model(odoo_model).write(odoo_ids, convert(args))

    @classmethod
    def cache_translation(cls, lang):
        """
            Récupère les traductions dans la langue `lang` des détails de tous les champs de l'objet
            Ces détails traduits sont stockés en cache dans chaque objet OdooField
        """
        def convert_lang(lang):
            res = lang.replace("-", "_")
            if "_" in res:
                res = res[:3] + res[3:].upper()
            return res
        trans_fields = settings.odoo.execute(cls._odoo_model, 'fields_get', [], context={"lang": convert_lang(lang)})
        for field in cls._meta.fields:
            if hasattr(field, "odoo_field") and trans_fields.get(field.name):
                field.odoo_field.translation_cache[lang] = trans_fields[field.name]

    def _convert_to_push(self, fieldnames=None):
        res = {}
        fieldnames = fieldnames or type(self)._get_odoo_fields()
        for field in type(self)._meta.fields:
            if hasattr(field, "odoo_field") and field.name in fieldnames:
                res[field.name] = field.odoo_field.convert_back(getattr(self, field.name))
        return res

    def odoo_push(self, fieldnames=None, client=None):
        """Saves a Django instance into Odoo

            If the instance has an *odoo_id* then we call `write`, otherwise we call `create`; 
            we only save the values of the fields indicated in `fieldnames`, or all
            of them if it is None.

            :todo: deal with one2many and many2many fields?
        """
        odoo_model = type(self)._odoo_model
        client = client or settings.odoo
        args = self._convert_to_push(fieldnames)
        if self.odoo_id:
            client.model(odoo_model).write([self.odoo_id], args)
            return self.odoo_id
        else:
            return client.model(odoo_model).create(args)

#     def __getattr__(self, name):
#         """Redefine getattr in order to translate translatable fields
#
#             Enables the translation of fields values based
#         """
#         print("getattr -----------------------", self._odoo_model, self.odoo_id, name)
#         for field in type(self)._meta.fields:
#             if (hasattr(field, "odoo_field") and field.odoo_field.translatable and
#                     field.name == name and self.odoo_id):
#                 return settings.odoo.read(self._odoo_model, self.odoo_id, fields=name)
#         return super(OdooModel, self).__getitem__()


class OdooUser(models.Model):
    user = models.OneToOneField(User, blank=False, related_name='odoo_user')

    def __init__(self, *args, **kwargs):
        config = getattr(settings, "ODOO_HOST", False)
        super(OdooUser, self).__init__(*args, **kwargs)
        passwd = kwargs.get('password') or caches["odoo_auth"].get('%s_credentials' % self.user.username)
        self.odoo_client = erppeek.Client("%s:%d" % (config['HOST'], config['PORT']), db=config['DB'],
                                          user=self.user.username, password=passwd, verbose=False)
