from django.conf import settings
from django.contrib.auth.models import User
import erppeek
from .models import OdooUser
from django.core.cache import caches
from django.db import transaction


class OdooAuthBackend(object):

    """
    Authenticate against the user in Odoo
    """
    @transaction.atomic
    def authenticate(self, username=None, password=None):
        config = getattr(settings, "ODOO_HOST", False)
        try:
            odoo_client = erppeek.Client("%s:%d" % (config['HOST'], config['PORT']), db=config['DB'],
                                         user=username, password=password, verbose=False)
        except:
            return None

        caches["odoo_auth"].set('%s_credentials' % username, password, None)

        try:
            user = User.objects.get(username=username)
            odoo_user = user.odoo_user
        except User.DoesNotExist:
            # Create a new user. Note that we can set password
            # to anything, because it won't be checked; the password
            # from Odoo will.
            user = User(username=username, password='get from Odoo')
            user.is_staff = False
            user.is_superuser = False
            user.save()
            odoo_user = OdooUser(user=user)
            odoo_user.save()
        odoo_user.odoo_client = odoo_client
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
