from builtins import str
from builtins import object
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from djchoices.choices import DjangoChoices, ChoiceItem

from future.utils import python_2_unicode_compatible

from bluebottle.fsm.triggers import TriggerMixin

from polymorphic.models import PolymorphicModel

from bluebottle.files.fields import ImageField
from bluebottle.initiatives.models import Initiative
from bluebottle.follow.models import Follow
from bluebottle.utils.models import ValidatedModelMixin, AnonymizationMixin
from bluebottle.utils.utils import get_current_host, get_current_language, clean_html


@python_2_unicode_compatible
class Activity(TriggerMixin, AnonymizationMixin, ValidatedModelMixin, PolymorphicModel):
    owner = models.ForeignKey(
        'members.Member',
        verbose_name=_('activity manager'),
        related_name='activities',
        on_delete=models.CASCADE
    )

    highlight = models.BooleanField(default=False,
                                    help_text=_('Highlight this activity to show it on homepage'))

    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)
    transition_date = models.DateTimeField(
        _('transition date'),
        help_text=_('Date of the last transition.'),
        null=True, blank=True
    )

    status = models.CharField(max_length=40)

    review_status = models.CharField(max_length=40, default='draft')

    initiative = models.ForeignKey(Initiative, related_name='activities', on_delete=models.CASCADE)

    office_location = models.ForeignKey(
        'geo.Location', verbose_name=_('office'),
        help_text=_("Office is set on activity level because the "
                    "initiative is set to 'global' or no initiative has been specified."),
        null=True, blank=True, on_delete=models.SET_NULL)

    title = models.CharField(_('Title'), max_length=255)
    slug = models.SlugField(_('Slug'), max_length=100, default='new')
    description = models.TextField(
        _('Description'), blank=True
    )

    image = ImageField(blank=True, null=True)

    video_url = models.URLField(
        _('video'),
        max_length=100,
        blank=True,
        null=True,
        default='',
        help_text=_(
            "Do you have a video pitch or a short movie that "
            "explains your activity? Cool! We can't wait to see it! "
            "You can paste the link to YouTube or Vimeo video here"
        )
    )
    segments = models.ManyToManyField(
        'segments.segment',
        verbose_name=_('Segment'),
        related_name='activities',
        blank=True
    )

    followers = GenericRelation('follow.Follow', object_id_field='instance_id')
    messages = GenericRelation('notifications.Message')

    follows = GenericRelation(Follow, object_id_field='instance_id')
    wallposts = GenericRelation('wallposts.Wallpost', related_query_name='activity_wallposts')

    auto_approve = True

    @property
    def activity_date(self):
        raise NotImplementedError

    @property
    def fallback_location(self):
        return self.initiative.location or self.office_location

    @property
    def stats(self):
        return {}

    @property
    def required_fields(self):
        if self.initiative_id and self.initiative.is_global:
            return ['office_location']
        else:
            return []

    class Meta(object):
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")
        permissions = (
            ('api_read_activity', 'Can view activity through the API'),
            ('api_read_own_activity', 'Can view own activity through the API'),
        )

    def __str__(self):
        return self.title or str(_('-empty-'))

    def save(self, **kwargs):
        if self.slug in ['', 'new']:
            if self.title and slugify(self.title):
                self.slug = slugify(self.title)
            else:
                self.slug = 'new'

        if not self.owner_id:
            self.owner = self.initiative.owner

        self.description = clean_html(self.description)

        super(Activity, self).save(**kwargs)

        if not self.segments.count():
            for segment in self.owner.segments.filter(segment_type__inherit=True).all():
                self.segments.add(segment)

    def get_absolute_url(self):
        domain = get_current_host()
        language = get_current_language()
        link = u"{}/{}/initiatives/activities/details/{}/{}/{}".format(
            domain, language,
            self.get_real_instance().__class__.__name__.lower(),
            self.pk,
            self.slug
        )
        return link

    @property
    def organizer(self):
        return self.contributors.instance_of(Organizer).first()


def NON_POLYMORPHIC_CASCADE(collector, field, sub_objs, using):
    # This fixing deleting related polymorphic objects through admin
    return models.CASCADE(collector, field, sub_objs.non_polymorphic(), using)


@python_2_unicode_compatible
class Contributor(TriggerMixin, AnonymizationMixin, PolymorphicModel):
    status = models.CharField(max_length=40)

    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)
    transition_date = models.DateTimeField(null=True, blank=True)
    contributor_date = models.DateTimeField(null=True, blank=True)

    activity = models.ForeignKey(
        Activity, related_name='contributors', on_delete=NON_POLYMORPHIC_CASCADE
    )
    user = models.ForeignKey(
        'members.Member', verbose_name=_('user'), null=True, blank=True, on_delete=models.CASCADE
    )

    @property
    def owner(self):
        return self.user

    @property
    def date(self):
        return self.activity.contributor_date

    class Meta(object):
        ordering = ('-created',)
        verbose_name = _('Contribution')
        verbose_name_plural = _('Contributions')

    def __str__(self):
        if self.user:
            return str(self.user)
        return str(_('Guest'))


@python_2_unicode_compatible
class Organizer(Contributor):
    class Meta(object):
        verbose_name = _("Activity owner")
        verbose_name_plural = _("Activity owners")

    class JSONAPIMeta(object):
        resource_name = 'contributors/organizers'


class Contribution(TriggerMixin, PolymorphicModel):
    status = models.CharField(max_length=40)

    created = models.DateTimeField(default=timezone.now)
    start = models.DateTimeField(_('start'), null=True, blank=True)
    end = models.DateTimeField(_('end'), null=True, blank=True)

    contributor = models.ForeignKey(
        Contributor, related_name='contributions', on_delete=NON_POLYMORPHIC_CASCADE
    )

    @property
    def owner(self):
        return self.contributor.user

    class Meta(object):
        ordering = ('-created',)
        verbose_name = _("Contribution amount")
        verbose_name_plural = _("Contribution amounts")

    def __str__(self):
        return str(_('Contribution amount'))


class EffortContribution(Contribution):

    class ContributionTypeChoices(DjangoChoices):
        organizer = ChoiceItem('organizer', label=_("Activity Organizer"))
        deed = ChoiceItem('deed', label=_("Deed particpant"))

    contribution_type = models.CharField(
        _('Contribution type'),
        max_length=20,
        choices=ContributionTypeChoices.choices,
    )

    class Meta(object):
        verbose_name = _("Effort")
        verbose_name_plural = _("Contributions")


from bluebottle.activities.signals import *  # noqa
from bluebottle.activities.wallposts import *  # noqa
from bluebottle.activities.states import *  # noqa
