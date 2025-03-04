from builtins import str
import json
from datetime import timedelta, date
import dateutil

from django.contrib.auth.models import Group, Permission
from django.contrib.gis.geos import Point
from django.test import tag
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django_elasticsearch_dsl.test import ESTestCase
from rest_framework import status

from bluebottle.files.tests.factories import ImageFactory

from bluebottle.deeds.tests.factories import DeedFactory, DeedParticipantFactory
from bluebottle.collect.tests.factories import CollectContributorFactory

from bluebottle.funding.tests.factories import FundingFactory, DonorFactory
from bluebottle.time_based.tests.factories import (
    DateActivityFactory, PeriodActivityFactory, DateParticipantFactory, PeriodParticipantFactory,
    DateActivitySlotFactory, SkillFactory
)
from bluebottle.initiatives.tests.factories import InitiativeFactory
from bluebottle.members.models import MemberPlatformSettings
from bluebottle.segments.tests.factories import SegmentFactory
from bluebottle.test.factory_models.accounts import BlueBottleUserFactory
from bluebottle.test.factory_models.geo import LocationFactory, GeolocationFactory, PlaceFactory, CountryFactory
from bluebottle.test.factory_models.projects import ThemeFactory
from bluebottle.test.utils import BluebottleTestCase, JSONAPITestClient


@override_settings(
    ELASTICSEARCH_DSL_AUTOSYNC=True,
    ELASTICSEARCH_DSL_AUTO_REFRESH=True
)
@tag('elasticsearch')
class ActivityListSearchAPITestCase(ESTestCase, BluebottleTestCase):
    def setUp(self):
        super(ActivityListSearchAPITestCase, self).setUp()

        self.client = JSONAPITestClient()
        self.url = reverse('activity-list')
        self.owner = BlueBottleUserFactory.create()

    def test_images(self):
        DateActivityFactory.create(
            owner=self.owner, review_status='approved', image=ImageFactory.create()
        )
        PeriodActivityFactory.create(review_status='approved', image=ImageFactory.create())
        FundingFactory.create(review_status='approved', image=ImageFactory.create())

        response = self.client.get(self.url, user=self.owner)

        for activity in response.json()['data']:
            self.assertEqual(
                activity['relationships']['image']['data']['type'],
                'images'
            )

    def test_no_filter(self):
        succeeded = DateActivityFactory.create(
            owner=self.owner, status='succeeded'
        )
        open = DateActivityFactory.create(status='open')
        DateActivityFactory.create(status='submitted')
        DateActivityFactory.create(status='closed')
        DateActivityFactory.create(status='cancelled')
        DateActivityFactory.create(status='rejected')

        response = self.client.get(self.url, user=self.owner)
        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][1]['id'], str(succeeded.pk))
        self.assertEqual(data['data'][0]['id'], str(open.pk))

        self.assertTrue('meta' in data['data'][0])

    def test_anonymous(self):
        succeeded = DateActivityFactory.create(
            owner=self.owner,
        )
        succeeded.initiative.states.submit(save=True)
        succeeded.initiative.states.approve(save=True)
        succeeded.states.submit(save=True)

        slot = succeeded.slots.get()
        slot.start = now() - timedelta(days=10)
        slot.save()

        DateParticipantFactory.create(
            activity=succeeded
        )

        open = DateActivityFactory.create(status='open')
        DateActivityFactory.create(status='submitted')
        DateActivityFactory.create(status='closed')

        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][1]['id'], str(succeeded.pk))
        self.assertEqual(data['data'][0]['id'], str(open.pk))

        self.assertTrue('meta' in data['data'][0])

    def setup_closed_segments(self):
        self.closed_segment = SegmentFactory.create(closed=True)
        self.open_segment = SegmentFactory.create()

        self.without_segment = DateActivityFactory.create(status='succeeded')

        self.with_open_segment = DateActivityFactory.create(status='succeeded')
        self.with_open_segment.segments.add(self.open_segment)

        self.with_closed_segment = DateActivityFactory.create(status='open')
        self.with_closed_segment.segments.add(self.closed_segment)

    def test_closed_segments_anonymous(self):
        self.setup_closed_segments()

        response = self.client.get(self.url)
        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][0]['id'], str(self.without_segment.pk))
        self.assertEqual(data['data'][1]['id'], str(self.with_open_segment.pk))

    def test_closed_segments_user(self):
        self.setup_closed_segments()

        user = BlueBottleUserFactory.create()
        user.segments.add(self.closed_segment)

        response = self.client.get(self.url, user=user)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 3)

        self.assertEqual(data['data'][0]['id'], str(self.without_segment.pk))
        self.assertEqual(data['data'][1]['id'], str(self.with_open_segment.pk))
        self.assertEqual(data['data'][2]['id'], str(self.with_closed_segment.pk))

    def test_filter_owner(self):
        DateActivityFactory.create(owner=self.owner, status='open')
        DateActivityFactory.create(status='open')

        response = self.client.get(
            self.url + '?filter[owner.id]={}'.format(self.owner.pk),
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertEqual(data['data'][0]['relationships']['owner']['data']['id'], str(self.owner.pk))

    def test_filter_type(self):
        DateActivityFactory.create(status='open')
        PeriodActivityFactory.create(status='open')
        FundingFactory.create(status='open')
        DeedFactory.create(status='open')

        response = self.client.get(
            self.url + '?filter[type]=funding',
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertEqual(data['data'][0]['type'], 'activities/fundings')

        response = self.client.get(
            self.url + '?filter[type]=deed',
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertEqual(data['data'][0]['type'], 'activities/deeds')

        response = self.client.get(
            self.url + '?filter[type]=time_based',
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 2)
        types = set(resource['type'] for resource in data['data'])
        self.assertEqual(
            types,
            {'activities/time-based/dates', 'activities/time-based/periods'}
        )

    def test_filter_expertise(self):
        skill = SkillFactory.create()

        first = DateActivityFactory.create(status='open', expertise=skill)
        second = PeriodActivityFactory.create(status='open', expertise=skill)
        PeriodActivityFactory.create(status='open')
        PeriodActivityFactory.create(status='open')

        response = self.client.get(
            self.url + '?filter[expertise.id]={}'.format(skill.id),
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 2)
        ids = [resource['id'] for resource in data['data']]
        self.assertTrue(str(first.pk) in ids)
        self.assertTrue(str(second.pk) in ids)

    def test_filter_expertise_empty(self):
        first = DateActivityFactory.create(status='open', expertise=None)
        second = PeriodActivityFactory.create(status='open', expertise=None)
        PeriodActivityFactory.create(status='open')
        PeriodActivityFactory.create(status='open')

        response = self.client.get(
            self.url + '?filter[expertise.id]=__empty__',
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 2)
        ids = [resource['id'] for resource in data['data']]
        self.assertTrue(str(first.pk) in ids)
        self.assertTrue(str(second.pk) in ids)

    def test_only_owner_permission(self):
        DateActivityFactory.create(owner=self.owner, status='open')
        DateActivityFactory.create(status='open')

        authenticated = Group.objects.get(name='Authenticated')
        authenticated.permissions.remove(
            Permission.objects.get(codename='api_read_activity')
        )
        authenticated.permissions.add(
            Permission.objects.get(codename='api_read_own_activity')
        )

        response = self.client.get(
            self.url,
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 1)

        self.assertEqual(data['data'][0]['relationships']['owner']['data']['id'], str(self.owner.pk))

    def test_initiative_location_filter(self):
        location = LocationFactory.create()
        initiative = InitiativeFactory.create(status='open', location=location)
        activity = DateActivityFactory.create(status='open', initiative=initiative)
        DateActivityFactory.create(status='open')

        response = self.client.get(
            self.url + '?filter[initiative_location.id]={}'.format(location.pk),
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertEqual(data['data'][0]['id'], str(activity.pk))

    def test_initiative_location_global_filter(self):
        location = LocationFactory.create()
        initiative = InitiativeFactory.create(status='open', location=location)
        activity = DateActivityFactory.create(
            status='open', initiative=initiative
        )

        global_initiative = InitiativeFactory.create(status='open', is_global=True)
        global_activity = DateActivityFactory.create(
            status='open', initiative=global_initiative, office_location=location
        )
        DateActivityFactory.create(status='open')

        response = self.client.get(
            self.url + '?filter[initiative_location.id]={}'.format(location.pk),
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)

        initiative_ids = [resource['id'] for resource in data['data']]
        self.assertTrue(str(activity.pk) in initiative_ids)
        self.assertTrue(str(global_activity.pk) in initiative_ids)

    def test_activity_date_filter(self):
        next_month = now() + dateutil.relativedelta.relativedelta(months=1)
        after = now() + dateutil.relativedelta.relativedelta(months=2)

        event = DateActivityFactory.create(
            status='open', slots=[]
        )
        DateActivitySlotFactory.create(activity=event, start=next_month)
        event_after = DateActivityFactory.create(
            status='open', slots=[]
        )
        DateActivitySlotFactory.create(activity=event_after, start=after)

        assignment = PeriodActivityFactory.create(
            status='open',
            deadline=next_month.date()
        )
        PeriodActivityFactory.create(
            status='open',
            deadline=after.date()
        )

        # Feature is not dealing with time. Disabling timezone check for test
        funding = FundingFactory.create(
            status='open',
            deadline=next_month
        )
        FundingFactory.create(
            status='open',
            deadline=after
        )

        start = next_month - dateutil.relativedelta.relativedelta(weeks=2)
        end = next_month + dateutil.relativedelta.relativedelta(weeks=2)
        response = self.client.get(
            self.url + '?filter[start]={}-{}-{}&filter[end]={}-{}-{}'.format(
                start.year, start.month, start.day,
                end.year, end.month, end.day),
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 5)

        found = [item['id'] for item in data['data']]
        self.assertTrue(str(event.pk) in found)
        self.assertTrue(str(assignment.pk) in found)
        self.assertTrue(str(funding.pk) in found)

        start = after - dateutil.relativedelta.relativedelta(weeks=2)
        end = after + dateutil.relativedelta.relativedelta(weeks=2)

        response = self.client.get(
            self.url + '?filter[start]={}-{}-{}&filter[end]={}-{}-{}'.format(
                start.year, start.month, start.day,
                end.year, end.month, end.day),
            user=self.owner
        )

        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 3)

        found = [item['id'] for item in data['data']]
        self.assertTrue(str(event.pk) not in found)
        self.assertTrue(str(assignment.pk) not in found)
        self.assertTrue(str(funding.pk) not in found)

    def test_activity_date_filter_slots(self):
        first = DateActivityFactory.create(
            status='open', slots=[]
        )
        for days in (2, 4, 6):
            DateActivitySlotFactory.create(
                activity=first,
                start=now() + timedelta(days=days)
            )

        second = DateActivityFactory.create(
            status='open', slots=[]
        )
        for days in (6, 8, 10):
            DateActivitySlotFactory.create(
                activity=second,
                start=now() + timedelta(days=days)
            )

        start = (now() + timedelta(days=2)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=2)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertTrue(str(first.pk) in [item['id'] for item in data['data']])

        start = (now() + timedelta(days=1)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=5)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertTrue(str(first.pk) in [item['id'] for item in data['data']])

        start = (now() + timedelta(days=1)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=6)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertTrue(str(first.pk) in [item['id'] for item in data['data']])
        self.assertTrue(str(second.pk) in [item['id'] for item in data['data']])

        start = (now() + timedelta(days=6)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=6)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertTrue(str(first.pk) in [item['id'] for item in data['data']])
        self.assertTrue(str(second.pk) in [item['id'] for item in data['data']])

        start = (now() + timedelta(days=7)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=7)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 0)

        start = (now() + timedelta(days=8)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=10)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertTrue(str(second.pk) in [item['id'] for item in data['data']])

        start = (now() + timedelta(days=12)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=30)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 0)

    def test_activity_date_filter_period(self):
        open_end = PeriodActivityFactory.create(
            status='open',
            start=date.today() + timedelta(days=5),
            deadline=None
        )

        open_start = PeriodActivityFactory.create(
            status='open',
            start=None,
            deadline=date.today() + timedelta(days=20)
        )

        first = PeriodActivityFactory.create(
            status='open',
            start=date.today() + timedelta(days=5),
            deadline=date.today() + timedelta(days=10)
        )

        second = PeriodActivityFactory.create(
            status='open',
            start=date.today() + timedelta(days=10),
            deadline=date.today() + timedelta(days=15)
        )

        third = PeriodActivityFactory.create(
            status='open',
            start=date.today() + timedelta(days=15),
            deadline=date.today() + timedelta(days=20)
        )

        start = (now() + timedelta(days=5)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=5)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 3)
        self.assertTrue(str(first.pk) in [item['id'] for item in data['data']])
        self.assertTrue(str(open_start.pk) in [item['id'] for item in data['data']])
        self.assertTrue(str(open_end.pk) in [item['id'] for item in data['data']])

        start = (now() + timedelta(days=14)).strftime('%Y-%m-%d')
        end = (now() + timedelta(days=18)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}&filter[end]={end}'.format(
                    start=start, end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 4)
        self.assertTrue(str(open_start.pk) in [item['id'] for item in data['data']])
        self.assertTrue(str(open_end.pk) in [item['id'] for item in data['data']])
        self.assertTrue(str(second.pk) in [item['id'] for item in data['data']])
        self.assertTrue(str(third.pk) in [item['id'] for item in data['data']])

        start = (now() + timedelta(days=25)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[start]={start}'.format(
                    start=start
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertTrue(str(open_end.pk) in [item['id'] for item in data['data']])

        end = (now() + timedelta(days=1)).strftime('%Y-%m-%d')
        data = json.loads(
            self.client.get(
                self.url + '?filter[end]={end}'.format(
                    end=end
                ),
                user=self.owner
            ).content
        )
        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertTrue(str(open_start.pk) in [item['id'] for item in data['data']])

    def test_activity_invalid_date_filter(self):
        next_month = now() + dateutil.relativedelta.relativedelta(months=1)
        after = now() + dateutil.relativedelta.relativedelta(months=2)

        event = DateActivityFactory.create(
            status='open', slots=[]
        )
        DateActivitySlotFactory.create(activity=event, start=next_month)
        event_after = DateActivityFactory.create(
            status='open', slots=[]
        )
        DateActivitySlotFactory.create(activity=event_after, start=after)

        PeriodActivityFactory.create(
            status='open',
            deadline=next_month.date()
        )
        response = self.client.get(
            self.url + '?filter[start]=0'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            self.url + '?filter[end]=2021-02-31'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_segment(self):
        segment = SegmentFactory.create()
        first = DateActivityFactory.create(
            status='open',
        )
        first.segments.add(segment)

        DateActivityFactory.create(
            status='open'
        )

        response = self.client.get(
            self.url + '?filter[segment.{}]={}'.format(
                segment.segment_type.slug, segment.pk
            ),
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertEqual(data['data'][0]['id'], str(first.pk))

    def test_filter_segment_mismatch(self):
        first = DateActivityFactory.create(
            status='open',
        )
        first_segment = SegmentFactory.create()
        first.segments.add(first_segment)
        second_segment = SegmentFactory.create()
        first.segments.add(second_segment)

        DateActivityFactory.create(
            status='open'
        )

        response = self.client.get(
            self.url + '?filter[segment.{}]={}'.format(
                first_segment.segment_type.slug, second_segment.pk
            ),
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 0)

    def test_search(self):
        first = DateActivityFactory.create(
            title='Lorem ipsum dolor sit amet',
            description="Lorem ipsum",
            status='open'
        )
        second = DateActivityFactory.create(title='Lorem ipsum dolor sit amet', status='open')

        response = self.client.get(
            self.url + '?filter[search]=lorem ipsum',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][0]['id'], str(first.pk))
        self.assertEqual(data['data'][1]['id'], str(second.pk))

    def test_search_page_size(self):
        DateActivityFactory.create_batch(
            12,
            title='Lorem ipsum dolor sit amet',
            description="Lorem ipsum",
            status='open'
        )
        response = self.client.get(
            self.url + '?page[size]=4'
        )
        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 12)
        self.assertEqual(len(data['data']), 4)

        response = self.client.get(
            self.url + '?page[size]=8'
        )
        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 12)
        self.assertEqual(len(data['data']), 8)

        response = self.client.get(
            self.url
        )
        data = json.loads(response.content)
        self.assertEqual(data['meta']['pagination']['count'], 12)
        self.assertEqual(len(data['data']), 8)

    def test_search_different_type(self):
        first = DateActivityFactory.create(
            title='Lorem ipsum dolor sit amet',
            description="Lorem ipsum",
            status='open'
        )
        second = PeriodActivityFactory.create(title='Lorem ipsum dolor sit amet', status='open')

        response = self.client.get(
            self.url + '?filter[search]=lorem ipsum',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][0]['id'], str(first.pk))
        self.assertEqual(data['data'][0]['type'], 'activities/time-based/dates')
        self.assertEqual(data['data'][1]['id'], str(second.pk))
        self.assertEqual(data['data'][1]['type'], 'activities/time-based/periods')

    def test_search_boost(self):
        first = DateActivityFactory.create(
            title='Something else',
            description='Lorem ipsum dolor sit amet',
            status='open'
        )
        second = DateActivityFactory.create(
            title='Lorem ipsum dolor sit amet',
            description="Something else",
            status='open'
        )

        response = self.client.get(
            self.url + '?filter[search]=lorem ipsum',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][0]['id'], str(second.pk))
        self.assertEqual(data['data'][1]['id'], str(first.pk))

    def test_search_formatted_address(self):
        activity1 = DateActivityFactory.create(
            title='Location! Location!',
            status='open'
        )
        location = GeolocationFactory.create(formatted_address='Roggeveenstraat')
        DateActivitySlotFactory.create(
            location=location,
            activity=activity1
        )
        DateActivitySlotFactory.create(
            activity=activity1,
            location=location)

        activity2 = DateActivityFactory.create(
            title='Nog een!',
            status='open'
        )
        DateActivitySlotFactory.create(
            location=location,
            activity=activity2
        )
        activity3 = DateActivityFactory.create(
            title='Nog een!',
            status='open'
        )
        DateActivitySlotFactory.create(
            activity=activity3
        )

        response = self.client.get(
            self.url + '?filter[search]=Roggeveenstraat',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][0]['id'], str(activity1.pk))
        self.assertEqual(data['data'][1]['id'], str(activity2.pk))

    def test_search_initiative_title(self):
        first = DateActivityFactory.create(
            initiative=InitiativeFactory.create(title='Test title'),
            status='open'
        )
        second = DateActivityFactory.create(
            title='Test title',
            status='open'
        )
        DateActivityFactory.create(
            status='open'
        )

        response = self.client.get(
            self.url + '?filter[search]=test title',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)
        self.assertEqual(data['data'][0]['id'], str(second.pk))
        self.assertEqual(data['data'][1]['id'], str(first.pk))

    def test_search_segment_name(self):
        first = DateActivityFactory.create(
            status='open',
        )
        first.segments.add(SegmentFactory(name='Online Marketing'))

        DateActivityFactory.create(
            status='open'
        )

        response = self.client.get(
            self.url + '?filter[search]=marketing',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 1)
        self.assertEqual(data['data'][0]['id'], str(first.pk))

    def test_sort_title(self):
        second = DateActivityFactory.create(title='B: something else', status='open')
        first = DateActivityFactory.create(title='A: something', status='open')
        third = DateActivityFactory.create(title='C: More', status='open')

        response = self.client.get(
            self.url + '?sort=alphabetical',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 3)
        self.assertEqual(data['data'][0]['id'], str(first.pk))
        self.assertEqual(data['data'][1]['id'], str(second.pk))
        self.assertEqual(data['data'][2]['id'], str(third.pk))

    def test_sort_activity_date(self):
        first = DateActivityFactory.create(
            status='open',
        )
        DateActivitySlotFactory.create(
            activity=first,
            start=now() + timedelta(days=10)
        )

        second = FundingFactory.create(
            status='open',
            deadline=now() + timedelta(days=9)
        )

        third = PeriodActivityFactory.create(
            status='open',
            start=now() + timedelta(days=4),
            deadline=now() + timedelta(days=11)
        )

        response = self.client.get(
            self.url + '?sort=date',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 3)

        self.assertEqual(data['data'][0]['id'], str(third.pk))
        self.assertEqual(data['data'][1]['id'], str(first.pk))
        self.assertEqual(data['data'][2]['id'], str(second.pk))

    def test_sort_matching_status(self):
        DateActivityFactory.create(status='closed')

        second = DateActivityFactory.create(
            owner=self.owner,
        )
        second.initiative.states.submit(save=True)
        second.initiative.states.approve(save=True)
        second.states.submit(save=True)

        slot = second.slots.get()
        slot.start = now() - timedelta(days=10)
        slot.save()

        DateParticipantFactory.create(
            activity=second
        )

        third = DateActivityFactory.create(
            status='open',
            capacity=1
        )
        DateParticipantFactory.create(activity=third)
        fourth = DateActivityFactory.create(status='running')
        DateParticipantFactory.create(activity=fourth)
        fifth = DateActivityFactory.create(status='open')
        DateParticipantFactory.create(activity=fifth)

        response = self.client.get(
            self.url + '?sort=popularity',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 4)

        self.assertEqual(data['data'][0]['id'], str(fifth.pk))
        self.assertEqual(data['data'][1]['id'], str(fourth.pk))
        self.assertEqual(data['data'][2]['id'], str(third.pk))
        self.assertEqual(data['data'][3]['id'], str(second.pk))

    def test_sort_matching_activity_date(self):
        first = DateActivityFactory.create(
            status='open',
        )
        DateActivitySlotFactory.create(
            activity=first,
            start=now() + timedelta(days=10)
        )

        second = FundingFactory.create(
            status='open',
            deadline=now() + timedelta(days=9)
        )

        third = PeriodActivityFactory.create(
            status='open',
            start=now() + timedelta(days=4),
            deadline=now() + timedelta(days=11)
        )

        fourth = PeriodActivityFactory.create(
            status='open',
            deadline=None,
            start=None
        )

        response = self.client.get(
            self.url + '?sort=popularity'
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 4)

        self.assertEqual(data['data'][0]['id'], str(second.pk))
        self.assertEqual(data['data'][1]['id'], str(first.pk))
        self.assertEqual(data['data'][2]['id'], str(third.pk))
        self.assertEqual(data['data'][3]['id'], str(fourth.pk))

    def test_sort_matching_skill(self):
        skill = SkillFactory.create()
        self.owner.skills.add(skill)
        self.owner.save()

        first = PeriodActivityFactory.create(status='full')

        second = PeriodActivityFactory.create(status='full', expertise=skill)

        third = PeriodActivityFactory.create(status='open')
        fourth = PeriodActivityFactory.create(status='open', expertise=skill)
        fifth = PeriodActivityFactory.create(status='open', expertise=None)

        response = self.client.get(
            self.url + '?sort=popularity',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 5)

        self.assertEqual(data['data'][0]['id'], str(fourth.pk))
        self.assertEqual(data['data'][1]['id'], str(fifth.pk))
        self.assertEqual(data['data'][2]['id'], str(third.pk))
        self.assertEqual(data['data'][3]['id'], str(second.pk))
        self.assertEqual(data['data'][4]['id'], str(first.pk))

    def test_sort_matching_theme(self):
        theme = ThemeFactory.create()
        self.owner.favourite_themes.add(theme)
        self.owner.save()

        initiative = InitiativeFactory.create(theme=theme)

        first = DateActivityFactory.create(status='open', capacity=1)
        DateParticipantFactory.create(activity=first)
        second = DateActivityFactory.create(
            status='open',
            initiative=initiative,
            capacity=1
        )
        DateParticipantFactory.create(activity=second)
        third = DateActivityFactory.create(status='open')
        DateParticipantFactory.create(activity=third)
        fourth = DateActivityFactory.create(status='open', initiative=initiative)

        response = self.client.get(
            self.url + '?sort=popularity',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 4)

        self.assertEqual(data['data'][0]['id'], str(fourth.pk))
        self.assertEqual(data['data'][1]['id'], str(third.pk))
        self.assertEqual(data['data'][2]['id'], str(second.pk))
        self.assertEqual(data['data'][3]['id'], str(first.pk))

    def test_sort_matching_location(self):
        self.owner.place = PlaceFactory.create(
            position=Point(20.0, 10.0)
        )
        self.owner.save()

        first = PeriodActivityFactory.create(status='full')

        second = PeriodActivityFactory.create(
            status='full',
            is_online=False,
            location=GeolocationFactory.create(position=Point(20.1, 10.1))
        )

        third = PeriodActivityFactory.create(
            status='open',
            is_online=False,
        )
        fourth = PeriodActivityFactory.create(
            status='open',
            is_online=False,
            location=GeolocationFactory.create(position=Point(20.1, 10.1))
        )

        fifth = PeriodActivityFactory.create(
            is_online=True,
            status='open',
            location=None
        )

        response = self.client.get(
            self.url + '?sort=popularity',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 5)

        self.assertEqual(data['data'][0]['id'], str(fourth.pk))
        self.assertEqual(data['data'][1]['id'], str(fifth.pk))
        self.assertEqual(data['data'][2]['id'], str(third.pk))
        self.assertEqual(data['data'][3]['id'], str(second.pk))
        self.assertEqual(data['data'][4]['id'], str(first.pk))

    def test_sort_contribution_count(self):

        deadline = now() + timedelta(days=2)
        first = FundingFactory.create(status='open', deadline=deadline)
        deadline = now() + timedelta(days=10)
        second = FundingFactory.create(status='open', deadline=deadline)
        third = FundingFactory.create(status='open', deadline=deadline)
        fourth = FundingFactory.create(status='open', deadline=deadline)
        fifth = FundingFactory.create(status='open', deadline=deadline)

        DonorFactory.create_batch(10, activity=fourth, status='succeeded')
        DonorFactory.create_batch(5, activity=fifth, status='succeeded')
        DonorFactory.create_batch(3, activity=third, status='succeeded')

        response = self.client.get(
            self.url + '?sort=popularity'
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 5)
        self.assertEqual(data['data'][0]['id'], str(first.pk))
        self.assertEqual(data['data'][1]['id'], str(fourth.pk))
        self.assertEqual(data['data'][2]['id'], str(fifth.pk))
        self.assertEqual(data['data'][3]['id'], str(third.pk))
        self.assertEqual(data['data'][4]['id'], str(second.pk))

    def test_filter_country(self):
        country1 = CountryFactory.create()
        country2 = CountryFactory.create()

        initiative1 = InitiativeFactory.create(place=GeolocationFactory.create(country=country1))
        initiative2 = InitiativeFactory.create(place=GeolocationFactory.create(country=country2))
        initiative3 = InitiativeFactory.create(place=GeolocationFactory.create(country=country1))
        initiative4 = InitiativeFactory.create(place=GeolocationFactory.create(country=country2))

        location1 = GeolocationFactory(country=country1)
        location2 = GeolocationFactory(country=country2)

        first = PeriodActivityFactory.create(status='full', initiative=initiative1, location=location1)
        PeriodParticipantFactory.create_batch(3, activity=first, status='accepted')

        second = PeriodActivityFactory.create(status='open', initiative=initiative3, location=location1)

        third = PeriodActivityFactory.create(status='full', initiative=initiative2, location=location2)
        PeriodParticipantFactory.create_batch(3, activity=third, status='accepted')

        PeriodActivityFactory.create(status='open', initiative=initiative4)

        response = self.client.get(
            self.url + '?sort=popularity&filter[country]={}'.format(country1.id),
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 2)

        self.assertEqual(data['data'][0]['id'], str(second.pk))
        self.assertEqual(data['data'][1]['id'], str(first.pk))

    def test_filter_office_country(self):
        country1 = CountryFactory.create()
        country2 = CountryFactory.create()
        office1 = LocationFactory.create(country=country1)
        office2 = LocationFactory.create(country=country2)

        initiative1 = InitiativeFactory.create(location=office1, place=None)
        initiative2 = InitiativeFactory.create(location=office2, place=None)
        initiative3 = InitiativeFactory.create(location=office1, place=None)
        initiative4 = InitiativeFactory.create(location=office2, place=None)

        location1 = GeolocationFactory(country=country1)

        first = PeriodActivityFactory.create(status='full', initiative=initiative1, is_online=True)
        PeriodParticipantFactory.create_batch(3, activity=first, status='accepted')

        second = PeriodActivityFactory.create(status='open', initiative=initiative3, is_online=True)

        third = PeriodActivityFactory.create(status='full', initiative=initiative2, location=location1)
        PeriodParticipantFactory.create_batch(3, activity=third, status='accepted')

        PeriodActivityFactory.create(status='open', initiative=initiative4, is_online=True)
        date = DateActivityFactory.create(status='open', initiative=initiative1)
        DateActivitySlotFactory.create(activity=date, status='open', is_online=True)

        response = self.client.get(
            self.url + '?sort=popularity&filter[country]={}'.format(country1.id),
            user=self.owner
        )

        data = json.loads(response.content)
        # Country filter should activities with initiative with office with that country,
        # but also activities with a (geo)location in that country
        self.assertEqual(data['meta']['pagination']['count'], 4)
        self.assertEqual(data['data'][0]['id'], str(second.pk))
        self.assertEqual(data['data'][1]['id'], str(date.pk))
        self.assertEqual(data['data'][2]['id'], str(first.pk))

    def test_sort_matching_office_location(self):
        self.owner.location = LocationFactory.create(position=Point(20.0, 10.0))
        self.owner.save()

        first = PeriodActivityFactory.create(status='full')

        second = PeriodActivityFactory.create(
            status='full',
            is_online=False,
            location=GeolocationFactory.create(position=Point(20.1, 10.1))
        )

        third = PeriodActivityFactory.create(status='open')
        fourth = PeriodActivityFactory.create(
            status='open',
            is_online=True,
        )
        fifth = PeriodActivityFactory.create(
            status='open',
            is_online=False,
            location=GeolocationFactory.create(position=Point(20.1, 10.1))
        )

        response = self.client.get(
            self.url + '?sort=popularity',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 5)

        self.assertEqual(data['data'][0]['id'], str(fifth.pk))
        self.assertEqual(data['data'][1]['id'], str(fourth.pk))
        self.assertEqual(data['data'][2]['id'], str(third.pk))
        self.assertEqual(data['data'][3]['id'], str(second.pk))
        self.assertEqual(data['data'][4]['id'], str(first.pk))

    def test_sort_matching_combined(self):
        theme = ThemeFactory.create()
        self.owner.favourite_themes.add(theme)

        skill = SkillFactory.create()
        self.owner.skills.add(skill)

        self.owner.location = LocationFactory.create(position=Point(20.0, 10.0))
        self.owner.save()

        initiative = InitiativeFactory.create(theme=theme)

        first = DateActivityFactory.create(
            status='open',
            initiative=initiative,
        )
        DateActivitySlotFactory.create(
            activity=first,
            is_online=False
        )

        second = PeriodActivityFactory.create(
            status='open',
            location=GeolocationFactory.create(position=Point(20.1, 10.1)),
            initiative=initiative,
            is_online=False
        )
        third = PeriodActivityFactory.create(
            status='open',
            location=GeolocationFactory.create(position=Point(20.1, 10.1)),
            initiative=initiative,
            expertise=skill,
            is_online=False
        )

        response = self.client.get(
            self.url + '?sort=popularity',
            user=self.owner
        )

        data = json.loads(response.content)

        self.assertEqual(data['meta']['pagination']['count'], 3)

        self.assertEqual(data['data'][0]['id'], str(third.pk))
        self.assertEqual(data['data'][1]['id'], str(second.pk))
        self.assertEqual(data['data'][2]['id'], str(first.pk))

    def test_limits(self):
        initiative = InitiativeFactory.create()
        DateActivityFactory.create_batch(
            7,
            status='open',
            initiative=initiative,
        )
        response = self.client.get(
            self.url + '?page[size]=150',
            user=self.owner
        )
        self.assertEqual(len(response.json()['data']), 7)

        response = self.client.get(
            self.url + '?page[size]=3',
            user=self.owner
        )
        self.assertEqual(len(response.json()['data']), 3)


class ActivityRelatedImageAPITestCase(BluebottleTestCase):
    def setUp(self):
        super(ActivityRelatedImageAPITestCase, self).setUp()
        self.client = JSONAPITestClient()
        self.owner = BlueBottleUserFactory.create()
        self.funding = FundingFactory.create(
            owner=self.owner,
        )
        self.related_image_url = reverse('related-activity-image-list')

        file_path = './bluebottle/files/tests/files/test-image.png'

        with open(file_path, 'rb') as test_file:
            response = self.client.post(
                reverse('image-list'),
                test_file.read(),
                content_type="image/png",
                format=None,
                HTTP_CONTENT_DISPOSITION='attachment; filename="some_file.jpg"',
                user=self.owner
            )

        self.file_data = json.loads(response.content)

    def test_create(self):
        data = {
            'data': {
                'type': 'related-activity-images',
                'relationships': {
                    'image': {
                        'data': {
                            'type': 'images',
                            'id': self.file_data['data']['id']
                        }
                    },
                    'resource': {
                        'data': {
                            'type': 'activities/fundings',
                            'id': self.funding.pk,
                        }
                    }
                }
            }
        }
        response = self.client.post(
            self.related_image_url,
            data=json.dumps(data),
            user=self.owner
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            response.json()['included'][1]['attributes']['links']['large'].split('?')[0],
            u'/api/activities/{}/related-image/600'.format(response.json()['data']['id'])
        )

    def test_create_non_owner(self):
        data = {
            'data': {
                'type': 'related-activity-images',
                'relationships': {
                    'image': {
                        'data': {
                            'type': 'images',
                            'id': self.file_data['data']['id']
                        }
                    },
                    'resource': {
                        'data': {
                            'type': 'activities/fundings',
                            'id': self.funding.pk,
                        }
                    }
                }
            }
        }
        response = self.client.post(
            self.related_image_url,
            data=json.dumps(data),
            user=BlueBottleUserFactory.create()
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ContributorListAPITestCase(BluebottleTestCase):
    def setUp(self):
        super(ContributorListAPITestCase, self).setUp()
        self.client = JSONAPITestClient()
        self.user = BlueBottleUserFactory.create()

        DateParticipantFactory.create_batch(2, user=self.user)
        PeriodParticipantFactory.create_batch(2, user=self.user)
        DonorFactory.create_batch(2, user=self.user, status='succeeded')
        DonorFactory.create_batch(2, user=self.user, status='new')
        DeedParticipantFactory.create_batch(2, user=self.user)
        CollectContributorFactory.create_batch(2, user=self.user)

        DateParticipantFactory.create()
        PeriodParticipantFactory.create()
        DonorFactory.create()
        DeedParticipantFactory.create()
        CollectContributorFactory.create()

        self.url = reverse('contributor-list')

    def test_get(self):
        response = self.client.get(
            self.url,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(len(data['data']), 10)

        for contributor in data['data']:
            self.assertTrue(
                contributor['type'] in (
                    'contributors/time-based/date-participants',
                    'contributors/time-based/period-participants',
                    'contributors/collect/contributors',
                    'contributors/deeds/participant',
                    'contributors/donations',
                )
            )
            self.assertTrue(contributor['type'])
            self.assertTrue(
                contributor['relationships']['activity']['data']['type'] in (
                    'activities/fundings',
                    'activities/deeds',
                    'activities/time-based/dates',
                    'activities/time-based/periods',
                    'activities/collects'
                )
            )

            if contributor['type'] in (
                'activities/time-based/date-participant',
                'activities/time-based/period-participant',
            ):
                self.assertTrue('total-duration' in contributor['attributes'])

        for i in data['included']:
            if i['type'] == 'activities/time-based/date':
                self.assertTrue('start' in i['attributes'])
                self.assertTrue('duration' in i['attributes'])
                self.assertTrue('slug' in i['attributes'])
                self.assertTrue('title' in i['attributes'])

            if i['type'] == 'activities/time-based/period':
                self.assertTrue('deadline' in i['attributes'])
                self.assertTrue('duration-type' in i['attributes'])
                self.assertTrue('duration' in i['attributes'])
                self.assertTrue('slug' in i['attributes'])
                self.assertTrue('title' in i['attributes'])

            if i['type'] == 'activities/funding':
                self.assertTrue('slug' in i['attributes'])
                self.assertTrue('title' in i['attributes'])

            if i['type'] == 'activities/deeds':
                self.assertTrue('slug' in i['attributes'])
                self.assertTrue('title' in i['attributes'])

    def test_get_anonymous(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_other_user(self):
        response = self.client.get(
            self.url,
            user=BlueBottleUserFactory.create()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(len(data['data']), 0)


@override_settings(
    ELASTICSEARCH_DSL_AUTOSYNC=True,
    ELASTICSEARCH_DSL_AUTO_REFRESH=True
)
@tag('elasticsearch')
class ActivityAPIAnonymizationTestCase(ESTestCase, BluebottleTestCase):
    anonymous_resource = {
        'id': 'anonymous',
        'type': 'members',
        'attributes': {
            'is-anonymous': True
        }
    }

    def setUp(self):
        super(ActivityAPIAnonymizationTestCase, self).setUp()
        self.member_settings = MemberPlatformSettings.load()

        self.client = JSONAPITestClient()
        self.owner = BlueBottleUserFactory.create()

    def test_activity_over_max_age(self):
        self.member_settings.anonymization_age = 300
        self.member_settings.save()

        activity = DateActivityFactory.create(
            created=now() - timedelta(days=400),
            status='open'
        )

        data = self.client.get(
            reverse('date-detail', args=(activity.id,))
        ).json()

        self.assertEqual(
            data['data']['relationships']['owner']['data']['id'], 'anonymous'
        )

        self.assertTrue(self.anonymous_resource in data['included'])

    def test_activity_not_over_max_age(self):
        self.member_settings.anonymization_age = 300
        self.member_settings.save()

        activity = DateActivityFactory.create(
            created=now() - timedelta(days=200),
            status='open'
        )

        data = self.client.get(
            reverse('date-detail', args=(activity.id,))
        ).json()

        self.assertEqual(
            data['data']['relationships']['owner']['data']['id'], str(activity.owner.pk)
        )

        self.assertTrue(self.anonymous_resource not in data['included'])

    def test_initiative_over_max_age(self):
        self.member_settings.anonymization_age = 300
        self.member_settings.save()

        initiative = InitiativeFactory.create(
            status='open',
            promoter=BlueBottleUserFactory.create(),
            reviewer=BlueBottleUserFactory.create(),
        )

        initiative.created = now() - timedelta(days=400)
        initiative.save()

        DateActivityFactory.create(
            initiative=initiative,
            created=now() - timedelta(days=400),
            status='open'
        )
        data = self.client.get(
            reverse('initiative-detail', args=(initiative.id,))
        ).json()

        self.assertEqual(
            data['data']['relationships']['owner']['data']['id'], 'anonymous'
        )

        self.assertEqual(
            data['data']['relationships']['activity-managers']['data'][0]['id'], 'anonymous'
        )

        self.assertEqual(
            data['data']['relationships']['reviewer']['data']['id'], 'anonymous'
        )

        included_activity = [
            included for included in data['included'] if
            included['type'] == 'activities/time-based/dates'
        ][0]

        self.assertEqual(
            included_activity['relationships']['owner']['data']['id'], 'anonymous'
        )

    def test_initiative_not_over_max_age(self):
        self.member_settings.anonymization_age = 300
        self.member_settings.save()

        initiative = InitiativeFactory.create(
            status='open',
            promoter=BlueBottleUserFactory.create(),
            reviewer=BlueBottleUserFactory.create(),
        )

        initiative.created = now() - timedelta(days=200)
        initiative.save()

        activity = DateActivityFactory.create(
            initiative=initiative,
            status='open'
        )
        data = self.client.get(
            reverse('initiative-detail', args=(initiative.id,))
        ).json()

        self.assertEqual(
            data['data']['relationships']['owner']['data']['id'], str(initiative.owner.pk)
        )

        self.assertEqual(
            data['data']['relationships']['activity-managers']['data'][0]['id'],
            str(initiative.activity_managers.first().pk)
        )

        self.assertEqual(
            data['data']['relationships']['reviewer']['data']['id'], str(initiative.reviewer.pk)
        )

        included_activity = [
            included for included in data['included'] if
            included['type'] == 'activities/time-based/dates'
        ][0]

        self.assertEqual(
            included_activity['relationships']['owner']['data']['id'], str(activity.owner.pk)
        )

    def test_participants_over_max_age(self):
        self.member_settings.anonymization_age = 300
        self.member_settings.save()

        activity = DateActivityFactory.create(
            created=now() - timedelta(days=400),
            status='open'
        )

        activity_data = self.client.get(
            reverse('date-detail', args=(activity.id,))
        ).json()

        DateParticipantFactory.create(
            activity=activity,
            created=now() - timedelta(days=350),
        )
        new_participant = DateParticipantFactory.create(
            activity=activity
        )

        data = self.client.get(
            activity_data['data']['relationships']['contributors']['links']['related'],
            user=self.owner
        ).json()
        self.assertEqual(
            data['data'][0]['relationships']['user']['data']['id'],
            'anonymous'
        )
        self.assertEqual(
            data['data'][1]['relationships']['user']['data']['id'],
            str(new_participant.user.pk)
        )
