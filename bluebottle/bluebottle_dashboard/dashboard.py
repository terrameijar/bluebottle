import importlib

import rules
from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard, DefaultAppIndexDashboard
from jet.dashboard.modules import LinkList

from bluebottle.activities.dashboard import RecentActivities
from bluebottle.funding.dashboard import RecentFunding, PayoutsReadForApprovalDashboardModule
from bluebottle.initiatives.dashboard import MyReviewingInitiatives, MyOfficeInitiatives, \
    MyOfficeSubRegionInitiatives, MyOfficeRegionInitiatives, RecentInitiatives
from bluebottle.initiatives.models import InitiativePlatformSettings
from bluebottle.members.dashboard import RecentMembersDashboard


class CustomIndexDashboard(Dashboard):
    columns = 2

    def init_with_context(self, context):
        self.available_children.append(modules.LinkList)

        # Initiatives
        self.children.append(MyReviewingInitiatives())
        self.children.append(RecentInitiatives())

        if hasattr(context, 'request'):
            user = context.request.user
            if user.location:
                self.children.append(MyOfficeInitiatives())
                if InitiativePlatformSettings.objects.get().enable_office_regions:
                    self.children.append(MyOfficeSubRegionInitiatives())
                    self.children.append(MyOfficeRegionInitiatives())

        # Activities
        self.children.append(RecentActivities())
        self.children.append(RecentFunding())

        # Payouts
        self.children.append(PayoutsReadForApprovalDashboardModule())

        # Other
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            10,
            column=0,
            order=0
        ))
        self.children.append(RecentMembersDashboard())
        if rules.test_rule('exportdb.can_export', context['request'].user):
            metrics_children = [
                {
                    'title': _('Export metrics'),
                    'url': reverse_lazy('exportdb_export'),
                },
            ]
            self.children.append(LinkList(
                _('Export Metrics'),
                children=metrics_children
            ))


class CustomAppIndexDashboard(DefaultAppIndexDashboard):

    def __new__(cls, context, **kwargs):
        try:
            mod = importlib.import_module("bluebottle.{}.dashboard".format(kwargs['app_label']))
            dash = mod.AppIndexDashboard(context, **kwargs)
            return dash
        except ImportError:
            return DefaultAppIndexDashboard(context, **kwargs)
