from rest_framework_json_api.serializers import PolymorphicModelSerializer

from bluebottle.activities.models import Contribution, Activity
from bluebottle.events.serializers import EventSerializer, ParticipantSerializer
from bluebottle.funding.serializers import FundingSerializer, DonationSerializer
from bluebottle.jobs.serializers import JobSerializer, JobParticipantSerializer


class ActivitySerializer(PolymorphicModelSerializer):

    polymorphic_serializers = [
        EventSerializer,
        FundingSerializer,
        JobSerializer
    ]

    class Meta:
        model = Activity

    class JSONAPIMeta:
        included_resources = [
            'owner',
            'initiative',
            'location'
        ]
        resource_name = 'events'

    included_serializers = {
        'image': 'bluebottle.initiatives.serializers.InitiativeImageSerializer',
        'owner': 'bluebottle.initiatives.serializers.MemberSerializer',
        'initiative': 'bluebottle.initiatives.serializers.InitiativeSerializer',
        'location': 'bluebottle.geo.serializers.ActivityPlaceSerializer',
    }


class ContributionSerializer(PolymorphicModelSerializer):

    polymorphic_serializers = [
        ParticipantSerializer,
        JobParticipantSerializer,
        DonationSerializer
    ]

    class Meta:
        model = Contribution
