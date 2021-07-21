from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from bluebottle.time_based.models import PeriodActivity, DateActivity
from bluebottle.utils.documents import MultiTenantIndex

from bluebottle.initiatives.models import Initiative, Theme
from bluebottle.geo.models import Geolocation
from bluebottle.categories.models import Category
from bluebottle.activities.models import Activity
from bluebottle.funding.models import Funding
from bluebottle.deeds.models import Deed
from bluebottle.members.models import Member


# The name of your index
initiative = MultiTenantIndex('initiatives')
# See Elasticsearch Indices API reference for available settings
initiative.settings(
    number_of_shards=1,
    number_of_replicas=0
)


@registry.register_document
@initiative.document
class InitiativeDocument(Document):
    title_keyword = fields.KeywordField(attr='title')
    title = fields.TextField(fielddata=True)
    story = fields.TextField()
    pitch = fields.TextField()
    status = fields.KeywordField()
    created = fields.DateField()

    owner = fields.NestedField(properties={
        'id': fields.KeywordField(),
        'full_name': fields.TextField()
    })
    promoter = fields.NestedField(properties={
        'id': fields.KeywordField(),
        'full_name': fields.TextField()
    })
    activity_managers = fields.NestedField(properties={
        'id': fields.KeywordField(),
        'full_name': fields.TextField()
    })
    activity_owners = fields.NestedField(properties={
        'id': fields.KeywordField(),
        'full_name': fields.TextField()
    })

    owner_id = fields.KeywordField()
    promoter_id = fields.KeywordField()
    reviewer_id = fields.KeywordField()

    theme = fields.NestedField(properties={
        'id': fields.KeywordField(),
    })
    categories = fields.NestedField(properties={
        'id': fields.LongField(),
        'slug': fields.KeywordField(),
    })

    activities = fields.NestedField(properties={
        'id': fields.LongField(),
        'title': fields.KeywordField(),
        'activity_date': fields.DateField(),
    })

    place = fields.NestedField(properties={
        'country': fields.LongField(attr='country.pk'),
        'province': fields.TextField(),
        'locality': fields.TextField(),
        'street': fields.TextField(),
        'postal_code': fields.TextField(),
    })

    location = fields.NestedField(
        properties={
            'id': fields.LongField(),
            'name': fields.TextField(),
            'city': fields.TextField(),
        }
    )

    class Django:
        model = Initiative
        related_models = (
            Geolocation,
            Member,
            Theme,
            Funding,
            PeriodActivity,
            DateActivity,
            Deed
        )

    def get_queryset(self):
        return super(InitiativeDocument, self).get_queryset().select_related(
            'theme', 'place', 'owner', 'promoter', 'reviewer', 'activity_manager',
            'location'
        ).prefetch_related('activities', 'categories')

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, (Theme, Geolocation, Category)):
            return related_instance.initiative_set.all()
        if isinstance(related_instance, Member):
            return list(related_instance.own_initiatives.all()) + list(related_instance.review_initiatives.all())
        if isinstance(related_instance, Activity):
            return [related_instance.initiative]

    def prepare_activities(self, instance):
        return [
            {
                'id': activity.pk,
                'title': activity.title,
                'activity_date': activity.activity_date
            } for activity in instance.activities.filter(
                status__in=(
                    'succeeded',
                    'open',
                    'partially_funded',
                    'full',
                    'running'
                )
            )
        ]

    def prepare_location(self, instance):
        if instance.is_global:
            return [{
                'id': activity.office_location.id,
                'name': activity.office_location.name,
                'city': activity.office_location.city
            } for activity in instance.activities.all() if activity.office_location]
        elif instance.location:
            return {
                'id': instance.location.id,
                'name': instance.location.name,
                'city': instance.location.city
            }

    def prepare_activity_owners(self, instance):
        return [
            {
                'id': activity.owner.pk,
                'full_name': activity.owner.full_name
            } for activity in instance.activities.all()
        ]
