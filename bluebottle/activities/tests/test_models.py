from django.test import TestCase

from bluebottle.initiatives.tests.factories import InitiativeFactory
from bluebottle.time_based.tests.factories import PeriodActivityFactory
from bluebottle.segments.tests.factories import SegmentFactory, SegmentTypeFactory
from bluebottle.test.factory_models.accounts import BlueBottleUserFactory
from bluebottle.test.factory_models.geo import LocationFactory


class ActivitySegmentsTestCase(TestCase):
    def setUp(self):

        team_type = SegmentTypeFactory.create(name='Team')
        self.team = SegmentFactory.create(name='Online Marketing', segment_type=team_type)
        self.other_team = SegmentFactory.create(name='Direct Marketing', segment_type=team_type)

        unit_type = SegmentTypeFactory.create(name='Unit')
        self.unit = SegmentFactory.create(name='Marketing', segment_type=unit_type)
        SegmentFactory.create(name='Communications', segment_type=unit_type)

        self.user = BlueBottleUserFactory()
        self.user.segments.add(self.team)
        self.user.segments.add(self.unit)

        super(ActivitySegmentsTestCase, self).setUp()

    def test_segments(self):
        activity = PeriodActivityFactory.create(owner=self.user)
        self.assertTrue(self.unit in activity.segments.all())
        self.assertTrue(self.team in activity.segments.all())

    def test_segments_already_set(self):
        activity = PeriodActivityFactory.create(owner=self.user, status='succeeded')
        self.user.segments.remove(self.team)
        self.user.segments.add(self.other_team)

        self.assertTrue(self.unit in activity.segments.all())
        self.assertTrue(self.team in activity.segments.all())
        self.assertFalse(self.other_team in activity.segments.all())

    def test_segments_already_set_open(self):
        activity = PeriodActivityFactory.create(owner=self.user, status='open')
        self.user.segments.remove(self.team)
        self.user.segments.add(self.other_team)

        self.assertTrue(self.unit in activity.segments.all())
        self.assertTrue(self.other_team in activity.segments.all())
        self.assertFalse(self.team in activity.segments.all())

    def test_segments_already_set_draft(self):
        activity = PeriodActivityFactory.create(owner=self.user, status='draft')
        self.user.segments.remove(self.team)
        self.user.segments.add(self.other_team)

        self.assertTrue(self.unit in activity.segments.all())
        self.assertTrue(self.other_team in activity.segments.all())
        self.assertFalse(self.team in activity.segments.all())

    def test_delete_segment(self):
        activity = PeriodActivityFactory.create(owner=self.user)

        self.team.delete()

        self.assertTrue(self.unit in activity.segments.all())
        self.assertFalse(self.team in activity.segments.all())

    def test_office_location_fallback(self):
        location = LocationFactory.create()
        activity = PeriodActivityFactory.create(
            initiative=InitiativeFactory.create(location=location)
        )
        self.assertEqual(activity.fallback_location, location)

    def test_office_location_fallback_both(self):
        location = LocationFactory.create()
        activity = PeriodActivityFactory.create(
            initiative=InitiativeFactory.create(location=location),
            office_location=LocationFactory.create()
        )
        self.assertEqual(activity.fallback_location, location)

    def test_office_location_fallback_activity(self):
        location = LocationFactory.create()
        activity = PeriodActivityFactory.create(
            initiative=InitiativeFactory.create(location=None),
            office_location=location
        )
        self.assertEqual(activity.fallback_location, location)

    def test_office_location_required(self):
        activity = PeriodActivityFactory.create(
            initiative=InitiativeFactory.create(is_global=True)
        )
        self.assertTrue('office_location' in activity.required_fields)

    def test_office_location_not_required(self):
        activity = PeriodActivityFactory.create(
            initiative=InitiativeFactory.create(is_global=False)
        )
        self.assertFalse('office_location' in activity.required_fields)
