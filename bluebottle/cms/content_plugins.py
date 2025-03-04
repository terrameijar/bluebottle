from builtins import object
from django import forms
from django.utils.translation import gettext_lazy as _
from fluent_contents.extensions import plugin_pool, ContentPlugin
from fluent_contents.forms import ContentItemForm

from bluebottle.cms.admin import (
    QuoteInline, StatInline, StepInline, LogoInline, ContentLinkInline,
    GreetingInline
)
from bluebottle.cms.models import (
    QuotesContent, StatsContent, ShareResultsContent, SupporterTotalContent,
    StepsContent, SlidesContent,
    CategoriesContent, LocationsContent, LogosContent, ProjectsMapContent,
    LinksContent, WelcomeContent, HomepageStatisticsContent,
    ActivitiesContent)


class CMSContentItemForm(ContentItemForm):
    # Normal ContentItemForm throws error when trying to delete
    # ContentPlugins that contain lists.
    # So we override the sort_order widget
    sort_order = forms.IntegerField(widget=forms.HiddenInput(), required=False, initial=1)


class CMSContentPlugin(ContentPlugin):
    form = CMSContentItemForm
    admin_form_template = 'admin/cms/content_item.html'

    class Media(object):
        css = {
            "all": ('admin/css/forms-nested.css', )
        }
        js = (
            'admin/js/inlines-nested.js',
            'js/csrf.js',
            'adminsortable/js/jquery-ui-django-admin.min.js',
            'adminsortable/js/admin.sortable.stacked.inlines.js'
        )


@plugin_pool.register
class QuotesBlockPlugin(CMSContentPlugin):
    model = QuotesContent
    inlines = [QuoteInline]
    category = _('Content')


@plugin_pool.register
class StatsBlockPlugin(CMSContentPlugin):
    model = StatsContent
    inlines = [StatInline]
    category = _('Stats')


@plugin_pool.register
class HomepageStatisticsBlockPlugin(CMSContentPlugin):
    model = HomepageStatisticsContent
    category = _('Stats')

    category = _('Homepage')


@plugin_pool.register
class ActivitiesBlockPlugin(CMSContentPlugin):
    model = ActivitiesContent
    raw_id_fields = ('activities', )
    category = _('Activities')


@plugin_pool.register
class ShareResultsBlockPlugin(CMSContentPlugin):
    model = ShareResultsContent
    category = _('Results')


@plugin_pool.register
class ProjectMapBlockPlugin(CMSContentPlugin):
    model = ProjectsMapContent
    category = _('Projects')


@plugin_pool.register
class SupporterTotalBlockPlugin(CMSContentPlugin):
    model = SupporterTotalContent
    category = _('Stats')


@plugin_pool.register
class SlidesBlockPlugin(CMSContentPlugin):
    model = SlidesContent

    category = _('Homepage')


@plugin_pool.register
class StepsBlockPlugin(CMSContentPlugin):
    model = StepsContent
    inlines = [StepInline]
    category = _('Homepage')


@plugin_pool.register
class CategoriesBlockPlugin(CMSContentPlugin):
    model = CategoriesContent
    raw_id_fields = ('categories', )
    category = _('Homepage')


@plugin_pool.register
class LocationsBlockPlugin(CMSContentPlugin):
    model = LocationsContent
    raw_id_fields = ('locations', )
    category = _('Homepage')


@plugin_pool.register
class LogosBlockPlugin(CMSContentPlugin):
    model = LogosContent
    inlines = [LogoInline]
    category = _('Homepage')


@plugin_pool.register
class LinksBlockPlugin(CMSContentPlugin):
    model = LinksContent
    inlines = [ContentLinkInline]
    category = _('Homepage')


@plugin_pool.register
class WelcomeBlockPlugin(CMSContentPlugin):
    model = WelcomeContent
    inlines = [GreetingInline]
    category = _('Homepage')
