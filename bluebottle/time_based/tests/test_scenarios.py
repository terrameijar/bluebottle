from bluebottle.test.factory_models.accounts import BlueBottleUserFactory
from bluebottle.test.utils import BluebottleTestCase, JSONAPITestClient
from bluebottle.time_based.tests.factories import DateActivityFactory, DateActivitySlotFactory
from bluebottle.time_based.tests.steps import api_user_joins_activity, assert_participant_status, \
    api_participant_transition, assert_status, assert_slot_participant_status, assert_not_slot_participant, \
    api_user_joins_slot, api_slot_participant_transition


class DateParticipantScenarioTestCase(BluebottleTestCase):

    def setUp(self):
        super().setUp()
        self.owner = BlueBottleUserFactory.create()
        self.supporter = BlueBottleUserFactory.create()
        self.activity = DateActivityFactory.create(status='open', owner=self.owner, slots=[])
        self.slot1 = DateActivitySlotFactory.create(activity=self.activity)
        self.slot2 = DateActivitySlotFactory.create(activity=self.activity)
        self.slot3 = DateActivitySlotFactory.create(activity=self.activity)
        self.slot4 = DateActivitySlotFactory.create(activity=self.activity)
        self.client = JSONAPITestClient()

    def test_user_joins_activity(self):
        api_user_joins_activity(self, self.activity, self.supporter)
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        assert_slot_participant_status(self, self.slot1, self.supporter, status='registered')
        assert_slot_participant_status(self, self.slot2, self.supporter, status='registered')
        assert_slot_participant_status(self, self.slot3, self.supporter, status='registered')
        assert_slot_participant_status(self, self.slot4, self.supporter, status='registered')

    def test_user_joins_review_activity_accepted(self):
        self.activity.review = True
        self.activity.save()
        api_user_joins_activity(self, self.activity, self.supporter)
        assert_participant_status(self, self.activity, self.supporter, status='new')
        api_participant_transition(self, self.activity, self.supporter,
                                   transition='accept', request_user=self.owner)
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        api_participant_transition(self, self.activity, self.supporter,
                                   transition='remove', request_user=self.owner)
        assert_participant_status(self, self.activity, self.supporter, status='rejected')
        api_participant_transition(self, self.activity, self.supporter,
                                   transition='accept', request_user=self.owner)
        assert_participant_status(self, self.activity, self.supporter, status='accepted')

    def test_user_withdraws_from_activity(self):
        api_user_joins_activity(self, self.activity, self.supporter)
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        api_participant_transition(self, self.activity, self.supporter, transition='withdraw')
        assert_participant_status(self, self.activity, self.supporter, status='withdrawn')
        api_participant_transition(self, self.activity, self.supporter, transition='reapply')
        assert_participant_status(self, self.activity, self.supporter, status='accepted')

    def test_user_withdraws_from_review_activity(self):
        self.activity.review = True
        self.activity.save()
        api_user_joins_activity(self, self.activity, self.supporter)
        assert_participant_status(self, self.activity, self.supporter, status='new')
        api_participant_transition(self, self.activity, self.supporter, transition='withdraw')
        assert_participant_status(self, self.activity, self.supporter, status='withdrawn')
        api_participant_transition(self, self.activity, self.supporter, transition='reapply')
        assert_participant_status(self, self.activity, self.supporter, status='new')
        api_participant_transition(self, self.activity, self.supporter,
                                   transition='reject', request_user=self.owner)
        assert_participant_status(self, self.activity, self.supporter, status='rejected')

    def test_user_fills_activity(self):
        self.activity.capacity = 1
        self.activity.save()
        api_user_joins_activity(self, self.activity, self.supporter)
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        assert_status(self, model=self.activity, status='full')
        api_participant_transition(self, self.activity, self.supporter, transition='withdraw')
        assert_participant_status(self, self.activity, self.supporter, status='withdrawn')
        assert_status(self, model=self.activity, status='open')
        api_participant_transition(self, self.activity, self.supporter, transition='reapply')
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        assert_status(self, model=self.activity, status='full')
        api_participant_transition(self, self.activity, self.supporter,
                                   transition='remove', request_user=self.owner)
        assert_participant_status(self, self.activity, self.supporter, status='rejected')
        assert_status(self, model=self.activity, status='open')

    def test_user_selects_slots(self):
        self.activity.slot_selection = 'free'
        self.activity.save()
        api_user_joins_activity(self, self.activity, self.supporter)
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        assert_not_slot_participant(self, self.slot1, self.supporter)
        assert_not_slot_participant(self, self.slot2, self.supporter)
        api_user_joins_slot(self, self.slot1, self.supporter)
        assert_slot_participant_status(self, self.slot1, self.supporter, status='registered')
        assert_not_slot_participant(self, self.slot2, self.supporter)
        api_user_joins_slot(self, self.slot2, self.supporter)
        assert_slot_participant_status(self, self.slot2, self.supporter, status='registered')

    def test_user_fills_slot(self):
        self.activity.slot_selection = 'free'
        self.activity.save()
        self.slot1.capacity = 1
        self.slot1.save()
        self.slot2.capacity = 2
        self.slot2.save()
        api_user_joins_activity(self, self.activity, self.supporter)
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        assert_not_slot_participant(self, self.slot1, self.supporter)
        assert_not_slot_participant(self, self.slot2, self.supporter)
        api_user_joins_slot(self, self.slot1, self.supporter)
        assert_slot_participant_status(self, self.slot1, self.supporter, status='registered')
        assert_status(self, self.slot1, 'full')
        api_slot_participant_transition(self, self.slot1, self.supporter, transition='withdraw')
        assert_slot_participant_status(self, self.slot1, self.supporter, status='withdrawn')
        assert_status(self, self.slot1, 'open')
        api_slot_participant_transition(self, self.slot1, self.supporter, transition='reapply')
        assert_slot_participant_status(self, self.slot1, self.supporter, status='registered')
        assert_status(self, self.slot1, 'full')
        api_participant_transition(self, self.activity, self.supporter, transition='withdraw')
        assert_participant_status(self, self.activity, self.supporter, status='withdrawn')
        assert_slot_participant_status(self, self.slot1, self.supporter, status='registered')
        assert_status(self, self.slot1, 'open')
        api_participant_transition(self, self.activity, self.supporter, transition='reapply')
        assert_participant_status(self, self.activity, self.supporter, status='accepted')
        assert_slot_participant_status(self, self.slot1, self.supporter, status='registered')
        assert_status(self, self.slot1, 'full')

        api_user_joins_slot(self, self.slot2, self.supporter)
        assert_slot_participant_status(self, self.slot2, self.supporter, status='registered')
        assert_status(self, self.slot2, 'open')
        api_user_joins_slot(self, self.slot2, self.supporter, status_code=400)

    def test_accept_more_users_to_slot_review_activity(self):
        self.activity.slot_selection = 'free'
        self.activity.review = True
        self.activity.save()
        self.slot1.capacity = 1
        self.slot1.save()
        self.slot2.capacity = 2
        self.slot2.save()
        supporter2 = BlueBottleUserFactory.create()
        supporter3 = BlueBottleUserFactory.create()
        api_user_joins_activity(self, self.activity, self.supporter)
        api_user_joins_activity(self, self.activity, supporter2)
        api_user_joins_activity(self, self.activity, supporter3)
        assert_participant_status(self, self.activity, self.supporter, status='new')
        api_user_joins_slot(self, self.slot1, self.supporter)
        api_user_joins_slot(self, self.slot1, supporter2)
        api_user_joins_slot(self, self.slot1, supporter3)
        api_user_joins_slot(self, self.slot2, self.supporter)
        api_user_joins_slot(self, self.slot2, supporter2)
        api_user_joins_slot(self, self.slot2, supporter3)
        assert_status(self, self.slot1, 'open')
        assert_status(self, self.slot2, 'open')
        self.assertEqual(
            self.slot1.accepted_participants.count(), 0,
            'Slots should not have any accepted members yet'
        )

        api_participant_transition(self, self.activity, self.supporter,
                                   transition='accept', request_user=self.owner)
        assert_status(
            self, self.slot1, 'full',
            'Slot1 should be full now.'
        )
        assert_status(
            self, self.slot2, 'open',
            'Slot2 still has spots left and should be open.'
        )

        api_participant_transition(self, self.activity, supporter2,
                                   transition='accept', request_user=self.owner)
        assert_status(self, self.slot1, 'full')
        assert_status(self, self.slot2, 'full')

        api_participant_transition(
            self, self.activity, supporter3,
            transition='accept', request_user=self.owner)

        assert_slot_participant_status(self, self.slot1, self.supporter, 'registered')
        assert_participant_status(self, self.activity, self.supporter, 'accepted')
        assert_participant_status(self, self.activity, supporter2, 'accepted')
        assert_participant_status(self, self.activity, supporter3, 'accepted')
        self.assertEqual(
            self.slot1.accepted_participants.count(), 3,
            'Slot1 should have 3 accepted participants, although capacity was only 1.'
        )
        self.assertEqual(
            self.slot2.accepted_participants.count(), 3,
            'Slot1 should have 3 accepted participants, although capacity was only 2.'
        )
        api_slot_participant_transition(self, self.slot2, supporter3, 'withdraw')
        assert_slot_participant_status(self, self.slot2, supporter3, 'withdrawn')
        self.assertEqual(
            self.slot2.accepted_participants.count(), 2,
            'Slot1 should now have 2 accepted participants'
        )
        assert_status(self, self.slot2, 'full')
        api_participant_transition(self, self.activity, supporter2, 'withdraw')
        assert_slot_participant_status(self, self.slot2, supporter2, 'registered')
        assert_status(
            self, self.slot2, 'open',
            'Slot2 should now be '
        )
