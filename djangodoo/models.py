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
        """Load records from Odoo

            On charge des données depuis Odoo dans une liste d'objets Django sur base d'une liste d'IDs
            On lit donc les données correspondant aux champs dont on a besoin,
            et on convertit les valeurs reçues en fonction du type de champ
            grâce aux méthodes définies dans `fields`. En effet, chaque champ "Django"
            généré depuis un champ "Odoo" contient une référence vers un objet
            "OdooField" nommé "odoo_field"
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
        """Enregistrement sur records multiples

            On enregistre les modification données par `args` sur Odoo pour
            les records liés aux objets Django `objs`
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
            print(lang)
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
        """Enregistrement d'une instance Django vers Odoo

            S'il y a un `odoo_id` on fait un `write`, sinon un `create` ; on n'enregistre que les champs
            indiqués dans `fieldnames`, ou tous si fieldnames est nul

            :todo: prendre en compte les one2many et many2many?
        """
        odoo_model = type(self)._odoo_model
        client = client or settings.odoo
        args = self._convert_to_push(fieldnames)
        if self.odoo_id:
            client.model(odoo_model).write([self.odoo_id], args)
            return self.odoo_id
        else:
            return client.model(odoo_model).create(args)


class OdooUser(models.Model):
    user = models.OneToOneField(User, blank=False, related_name='odoo_user')

    def __init__(self, *args, **kwargs):
        config = getattr(settings, "ODOO_HOST", False)
        super(OdooUser, self).__init__(*args, **kwargs)
        passwd = kwargs.get('password') or caches["odoo_auth"].get('%s_credentials' % self.user.username)
        self.odoo_client = erppeek.Client("%s:%d" % (config['HOST'], config['PORT']), db=config['DB'],
                                          user=self.user.username, password=passwd, verbose=False)
