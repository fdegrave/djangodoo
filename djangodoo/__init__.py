# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.models.signals import class_prepared
from django.core.mail import send_mail
import erppeek
from .fields import convert_field
import logging

from time import sleep
import traceback

logger = logging.getLogger(__name__)


def set_auth_cache():
    settings.CACHES = settings.CACHES or {}
    settings.CACHES["odoo_auth"] = {'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
                                    'LOCATION': '127.0.0.1:18069'}


def set_odoo_client():
    config = getattr(settings, "ODOO_HOST", False)

    logger.info("Setting up the Odoo client...")
    max_retry_attempts = getattr(settings, "ODOO_MAX_RETRY_ATTEMPTS", 3)
    retry_delay = getattr(settings, "ODOO_RETRY_DELAY", 5)

    def _connect(retry_cnt):
        try:
            settings.odoo = erppeek.Client("%s:%d" % (config['HOST'], config['PORT']), db=config['DB'],
                                           user=config['USER'], password=config['PASSWORD'], verbose=False)
            settings.odoo.context = {"lang": settings.LANGUAGE_CODE}
            settings.odoo_models = {}
            settings.deferred_m2o = {}
            settings.deferred_o2m = {}
        except:
            logger.warn('Failed to connect to a running Odoo server.')
            logger.warn('Waiting {} [s] before the next attempt...'.format(retry_delay))
            logger.warn('{} trials left...'.format(max_retry_attempts-retry_cnt))
            sleep(retry_delay)
            if retry_cnt < max_retry_attempts:
                _connect(retry_cnt + 1)
            else:
                logger.error('Unable to connect to a running Odoo server. Aborting.')
                mail_config = getattr(settings, "ODOO_EMAIL_NOTIFICATION", False)
                mail_content = """Unable to connect to a running Odoo server. Your application may have failed to start up due to a connection problem with an Odoo instance.
                
                Djangodoo tried to reconnect {} times, waiting {} seconds between each attempt. Still, the server could not be reached.

                The problem occured with the following host configuration:
                    
                    USER: {}
                    HOST: {}
                    PORT: {}
                    DB: {}

                And here is the traceback of the exception raised during the last attempt:


                {}
                    
                """.format(max_retry_attempts, retry_delay, config['USER'], config['HOST'], config['PORT'], config['DB'], traceback.format_exc())
                html_content = """<p>Unable to connect to a running Odoo server. Your application may have failed to start up due to a connection problem with an Odoo instance.</p>
                
                <p>Djangodoo tried to reconnect <b>{} times</b>, waiting <b>{} seconds</b> between each attempt. Still, the server could not be reached.</p>

                <p>The problem occured with the following host configuration:</p>
                
                <div style="border-left: 1px solid gray; padding-left: 10px;">
                    USER: {}<br>
                    HOST: {}<br>
                    PORT: {}<br>
                    DB: {}<br>
                </div>

                <p>And here is the traceback of the exception raised during the last attempt:</p>

                <pre>

                {}

                </pre>
                    
                """.format(max_retry_attempts, retry_delay, config['USER'], config['HOST'], config['PORT'], config['DB'], traceback.format_exc())
                if mail_config:
                    logger.info('Sending an email notification to the administrator...')
                    send_mail("APPLICATION FAILURE - DJANGODOO",
                        mail_content,
                        getattr(settings, "DEFAULT_FROM_EMAIL", "djangodoo@example.com"),
                        mail_config["RECIPIENTS"],
                        html_message=html_content,
                        fail_silently=False)
                raise

    _connect(0)


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
logger.info("Done initializing Djangodoo.")
