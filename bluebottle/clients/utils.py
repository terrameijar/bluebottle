# -*- coding: utf-8 -*-

import importlib
import itertools
import logging
import re
from collections import namedtuple, defaultdict

from babel.numbers import get_currency_symbol, get_currency_name
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, ProgrammingError
from django.utils.translation import get_language
from djmoney_rates.exceptions import CurrencyConversionException
from djmoney_rates.utils import get_rate
from tenant_extras.utils import get_tenant_properties

from bluebottle.clients import properties
from bluebottle.funding_flutterwave.utils import get_flutterwave_settings
from bluebottle.funding_stripe.utils import get_stripe_settings
from bluebottle.payouts.utils import get_payout_settings

logger = logging.getLogger(__name__)


class LocalTenant(object):
    def __init__(self, tenant=None, clear_tenant=False):
        self.clear_tenant = clear_tenant
        self.previous_tenant = None

        if tenant:
            self.previous_tenant = connection.tenant
            self.tenant = tenant
        else:
            self.tenant = connection.tenant

    def __enter__(self):
        if self.tenant:
            connection.set_tenant(self.tenant)
            properties.set_tenant(self.tenant)
            ContentType.objects.clear_cache()

    def __exit__(self, type, value, traceback):
        if self.clear_tenant:
            try:
                del properties.tenant
                del properties.tenant_properties
            except AttributeError:
                logger.info("Attempted to clear missing tenant properties.")
        elif self.previous_tenant:
            connection.set_tenant(self.previous_tenant)
            properties.set_tenant(self.previous_tenant)
            ContentType.objects.clear_cache()


def tenant_url():
    # workaround for development setups. Assume port 8000
    domain = connection.tenant.domain_url

    if domain.endswith("localhost"):
        return "http://{0}:8000".format(domain)
    return "https://{0}".format(domain)


def tenant_name():
    return connection.tenant.name


def tenant_site():
    """ somewhat simulates the old 'Site' object """
    return namedtuple('Site', ['name', 'domain'])(tenant_name(),
                                                  connection.tenant.domain_url)


def get_min_amounts(methods):
    result = defaultdict(list)
    for method in methods:
        for currency, data in method['currencies'].items():
            result[currency].append(data.get('min_amount', 0))

    return dict((currency, min(amounts)) for currency, amounts in result.items())


def get_currencies():
    properties = get_tenant_properties()

    currencies = set(itertools.chain(*[
        method['currencies'].keys() for method in properties.PAYMENT_METHODS
    ]))
    min_amounts = get_min_amounts(properties.PAYMENT_METHODS)

    currencies = [{
        'code': code,
        'name': get_currency_name(code),
        'symbol': get_currency_symbol(code).replace('US$', '$')
    } for code in currencies]

    for currency in currencies:
        if currency['code'] in min_amounts:
            currency['minAmount'] = min_amounts[currency['code']]

        try:
            currency['rate'] = get_rate(currency['code'])
        except (CurrencyConversionException, ProgrammingError):
            currency['rate'] = 1

    return currencies


def get_user_site_links(user):
    from bluebottle.cms.models import SiteLinks

    try:
        site_links = SiteLinks.objects.get(language__code=get_language())
    except SiteLinks.DoesNotExist:
        site_links = SiteLinks.objects.first()

    # If no site links set, just return empty
    if not site_links:
        return {}

    response = {
        'hasCopyright': site_links.has_copyright,
        'groups': []
    }

    for group in site_links.link_groups.all():
        links = []

        for link in group.links.all():
            allowed = True
            if link.link_permissions.exists():
                # Check permissions
                for perm in link.link_permissions.all():
                    # has_perm  present allowed
                    # yes       yes     yes
                    # yes       no      no
                    # no        yes     no
                    # no        no      yes
                    allowed = (user.has_perm(perm.permission) == perm.present) and allowed

            if not allowed:
                continue

            link_data = {
                'title': link.title,
                'isHighlighted': link.highlight,
                'sequence': link.link_order
            }

            if link.component:
                link_data['route'] = link.component
            if link.component_id:
                link_data['param'] = link.component_id
            elif link.external_link:
                link_data['route'] = link.external_link
                link_data['external'] = True

            links.append(link_data)

        response['groups'].append({
            'title': group.title,
            'name': group.name,
            'sequence': group.group_order,
            'links': links
        })

    return response


def get_platform_settings(name):
    app_name, model_name = name.split('.')
    model_app_name = 'bluebottle.{}.models'.format(app_name)
    settings_class = getattr(importlib.import_module(model_app_name), model_name)
    settings_object = settings_class.load()
    serializer_app_name = 'bluebottle.{}.serializers'.format(app_name)
    serializer_class = getattr(importlib.import_module(serializer_app_name), "{}Serializer".format(model_name))
    return serializer_class(settings_object).to_representation(settings_object)


def get_public_properties(request):
    """

        Dynamically populate a tenant context with exposed tenant specific properties
        from reef/clients/client_name/properties.py.

        The context processor looks in tenant settings for the uppercased variable names that are defined in
        "EXPOSED_TENANT_PROPERTIES" to generate the context.

        Example:

        EXPOSED_TENANT_PROPERTIES = ['mixpanel', 'analytics']

        This adds the value of the keys MIXPANEL and ANALYTICS from the settings file.

    """

    config = {}

    properties = get_tenant_properties()

    props = None

    try:
        props = getattr(properties, 'EXPOSED_TENANT_PROPERTIES')
    except AttributeError:
        pass

    if not props:
        try:
            props = getattr(settings, 'EXPOSED_TENANT_PROPERTIES')
        except AttributeError:
            return config

    # First load tenant settings that should always be exposed
    if connection.tenant:

        current_tenant = connection.tenant
        properties = get_tenant_properties()

        config = {
            'mediaUrl': getattr(properties, 'MEDIA_URL'),
            'defaultAvatarUrl': "/images/default-avatar.png",
            'currencies': get_currencies(),
            'defaultCurrency': getattr(properties, 'DEFAULT_CURRENCY', 'EUR'),
            'logoUrl': "/images/logo.svg",
            'mapsApiKey': getattr(properties, 'MAPS_API_KEY', ''),
            'donationsEnabled': getattr(properties, 'DONATIONS_ENABLED', True),
            'siteName': current_tenant.name,
            'languages': [{'code': lang[0], 'name': lang[1]} for lang in getattr(properties, 'LANGUAGES')],
            'languageCode': get_language(),
            'siteLinks': get_user_site_links(request.user),
            'platform': {
                'payouts': get_payout_settings(),
                'content': get_platform_settings('cms.SitePlatformSettings'),
                'projects': get_platform_settings('projects.ProjectPlatformSettings'),
                'initiatives': get_platform_settings('initiatives.InitiativePlatformSettings'),
                'analytics': get_platform_settings('analytics.AnalyticsPlatformSettings'),
                'members': get_platform_settings('members.MemberPlatformSettings'),
            }
        }

        try:
            config['platform']['stripe'] = get_stripe_settings()
        except ImproperlyConfigured:
            pass
        try:
            config['platform']['flutterwave'] = get_flutterwave_settings()
        except ImproperlyConfigured:
            pass

        try:
            config['readOnlyFields'] = {
                'user': properties.TOKEN_AUTH.get('assertion_mapping', {}).keys()
            }
        except AttributeError:
            pass

    else:
        config = {}

    # snake_case to CamelCase
    def _camelize(s):
        return re.sub('_.', lambda x: x.group()[1].upper(), s)

    # Now load the tenant specific properties
    for item in props:
        try:
            parts = item.split('.')
            if len(parts) == 2:
                # get parent and child details
                parent = getattr(properties, parts[0].upper())
                parent_key = _camelize(parts[0])
                child_key = _camelize(parts[1])

                # skip if the child property does not exist
                try:
                    value = parent[parts[1]]
                except KeyError:
                    continue

                if parent_key not in config:
                    config[parent_key] = {}
                config[parent_key][child_key] = value

            elif len(parts) > 2:
                logger.info("Depth is too great for exposed property: {}".format(item))

            else:
                # Use camelcase for setting keys (convert from snakecase)
                key = _camelize(item)
                config[key] = getattr(properties, item.upper())
        except AttributeError:
            pass

    return config
