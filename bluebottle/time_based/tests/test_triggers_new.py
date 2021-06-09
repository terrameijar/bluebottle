from datetime import timedelta, date

from django.utils.timezone import now

from bluebottle.activities.messages import ActivityExpiredNotification, ActivitySucceededNotification, \
    ActivityRejectedNotification, ActivityCancelledNotification, ActivityRestoredNotification
from bluebottle.test.utils import TriggerTestCase
from bluebottle.test.factory_models.accounts import BlueBottleUserFactory

from bluebottle.activities.states import OrganizerStateMachine, EffortContributionStateMachine
from bluebottle.activities.effects import SetContributionDateEffect
from bluebottle.time_based.messages import (
    DeadlineChangedNotification, ActivitySucceededManuallyNotification, NewParticipantNotification,
    ParticipantAddedOwnerNotification, ParticipantAddedNotification,
    ParticipantAcceptedNotification
)

from bluebottle.time_based.tests.factories import (
    DateActivityFactory, DateParticipantFactory, DateActivitySlotFactory,
    PeriodActivityFactory, PeriodParticipantFactory, SlotParticipantFactory
)

from bluebottle.time_based.models import (
    PeriodActivity
)

from bluebottle.time_based.effects import (
    ActiveTimeContributionsTransitionEffect, RescheduleOverallPeriodActivityDurationsEffect,
    ClearDeadlineEffect, SetEndDateEffect, UnsetCapacityEffect,
    CreateSlotParticipantsForSlotsEffect, RescheduleSlotDurationsEffect,
    CreatePeriodTimeContributionEffect, CreatePreparationTimeContributionEffect
)

from bluebottle.follow.effects import (FollowActivityEffect, UnFollowActivityEffect)

from bluebottle.time_based.states import (
    TimeBasedStateMachine, DateStateMachine, DateParticipantStateMachine, DateActivitySlotStateMachine,
    PeriodStateMachine, PeriodParticipantStateMachine, TimeContributionStateMachine
)

from bluebottle.initiatives.tests.factories import InitiativeFactory
from bluebottle.test.factory_models.geo import GeolocationFactory


class ActivityTriggerTestCase():
    def test_submit(self):
        self.create()
        self.model.states.submit()

        with self.execute():
            self.assertTransitionEffect(DateStateMachine.auto_approve)
            self.assertTransitionEffect(OrganizerStateMachine.succeed, self.model.organizer)
            self.assertEffect(SetContributionDateEffect, self.model.organizer.contributions.first())

    def test_reject(self):
        self.test_submit()

        self.participant_factory.create(activity=self.model)

        self.model.states.reject()

        with self.execute():
            self.assertEffect(
                ActiveTimeContributionsTransitionEffect(TimeContributionStateMachine.fail)
            )
            self.assertNotificationEffect(ActivityRejectedNotification)
            self.assertTransitionEffect(
                OrganizerStateMachine.fail, self.model.organizer
            )

            self.assertTransitionEffect(
                TimeContributionStateMachine.fail, self.model.organizer.contributions.first()
            )

    def test_cancel(self):
        self.test_submit()

        self.participant_factory.create(activity=self.model)

        self.model.states.cancel()

        with self.execute():
            self.assertEffect(
                ActiveTimeContributionsTransitionEffect(TimeContributionStateMachine.fail)
            )
            self.assertNotificationEffect(ActivityCancelledNotification)
            self.assertTransitionEffect(
                OrganizerStateMachine.fail, self.model.organizer
            )

            self.assertTransitionEffect(
                TimeContributionStateMachine.fail, self.model.organizer.contributions.first()
            )

    def test_restore(self):
        self.test_submit()

        self.participant_factory.create(activity=self.model)

        self.model.states.cancel(save=True)
        self.model.states.restore()

        with self.execute():
            self.assertEffect(
                ActiveTimeContributionsTransitionEffect(TimeContributionStateMachine.reset)
            )
            self.assertNotificationEffect(ActivityRestoredNotification)
            self.assertTransitionEffect(
                OrganizerStateMachine.reset, self.model.organizer
            )

            self.assertTransitionEffect(
                TimeContributionStateMachine.reset, self.model.organizer.contributions.first()
            )

    def test_change_registration_deadline_passed(self):
        self.test_submit()

        self.model.registration_deadline = date.today() - timedelta(days=1)

        with self.execute():
            self.assertTransitionEffect(
                TimeBasedStateMachine.lock
            )

    def test_change_registration_deadline_future(self):
        self.test_change_registration_deadline_passed()

        self.model.registration_deadline = date.today() + timedelta(days=1)

        with self.execute():
            self.assertTransitionEffect(
                TimeBasedStateMachine.reopen
            )

    def test_change_capacity_reopen(self):
        self.defaults['capacity'] = 1

        self.test_submit()

        self.participant_factory.create(activity=self.model)
        
        self.model.capacity = 2

        with self.execute():
            self.assertTransitionEffect(DateStateMachine.reopen)

    def test_change_capacity_lock(self):
        self.defaults['capacity'] = 2

        self.test_submit()

        self.participant_factory.create(activity=self.model)
        
        self.model.capacity = 1

        with self.execute():
            self.assertTransitionEffect(DateStateMachine.lock)

    def test_change_capacity_registration_deadline_passed(self):
        self.defaults['registration_deadline'] = date.today() - timedelta(days=1)
        self.test_submit()

        self.participant_factory.create(activity=self.model)
        
        self.model.capacity = 1

        with self.execute():
            self.assertNoTransitionEffect(DateStateMachine.lock)
            self.assertNoTransitionEffect(DateStateMachine.reopen)


class DateActivityTriggersTestCase(ActivityTriggerTestCase, TriggerTestCase):
    factory = DateActivityFactory
    participant_factory = DateParticipantFactory

    def setUp(self):
        self.owner = BlueBottleUserFactory.create()
        self.staff_user = BlueBottleUserFactory.create(is_staff=True)

        initiative = InitiativeFactory.create()
        initiative.states.submit()
        initiative.states.approve(save=True)

        self.defaults = {
            'initiative': initiative,
            'owner': self.owner,
            'slots': [{
                'start': now().replace(
                    microsecond=0, second=0, minute=0, hour=12
                ) + timedelta(days=10),
                'duration': timedelta(hours=2),
            }]
        }
        super().setUp()

    def change_slot_selection(self):
        self.test_submit()
        self.model.slot_selection = 'free'

        with self.execute():
            self.assertEffect(UnsetCapacityEffect)


class PeriodActivityTriggersTestCase(ActivityTriggerTestCase, TriggerTestCase):
    factory = PeriodActivityFactory
    participant_factory = PeriodParticipantFactory

    def setUp(self):
        self.owner = BlueBottleUserFactory.create()
        self.staff_user = BlueBottleUserFactory.create(is_staff=True)

        initiative = InitiativeFactory.create()
        initiative.states.submit()
        initiative.states.approve(save=True)

        self.defaults = {
            'initiative': initiative,
            'owner': self.owner,
            'registration_deadline': date.today() + timedelta(days=1),
            'start': date.today() + timedelta(days=2),
            'deadline': date.today() + timedelta(days=10)
        }
        super().setUp()

    def test_change_start(self):
        self.test_submit()

        self.model.start = date.today() - timedelta(days=3)

        with self.execute():
            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_start_future(self):
        self.test_submit()

        self.participant_factory.create(activity=self.model)

        self.model.start = date.today() + timedelta(days=4)

        with self.execute():
            self.assertNotificationEffect(DeadlineChangedNotification)

            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_deadline_future(self):
        self.test_submit()

        self.participant_factory.create(activity=self.model)

        self.model.deadline = date.today() + timedelta(days=2)

        with self.execute():
            self.assertNotificationEffect(DeadlineChangedNotification)

            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_deadline_expire(self):
        self.test_submit()

        self.model.start = date.today() - timedelta(days=3)
        self.model.deadline = date.today() - timedelta(days=2)

        with self.execute():
            self.assertTransitionEffect(
                PeriodStateMachine.expire
            )

            self.assertTransitionEffect(
                OrganizerStateMachine.fail, self.model.organizer
            )

            self.assertTransitionEffect(
                EffortContributionStateMachine.fail, self.model.organizer.contributions.get()
            )

            self.assertNotificationEffect(ActivityExpiredNotification)

            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_deadline_succeed(self):
        self.test_submit()

        self.participant = self.participant_factory.create(activity=self.model)

        self.model.start = date.today() - timedelta(days=3)
        self.model.deadline = date.today() - timedelta(days=2)

        with self.execute():
            self.assertTransitionEffect(
                PeriodStateMachine.succeed
            )
            self.assertTransitionEffect(
                PeriodParticipantStateMachine.succeed, self.participant
            )

            self.assertTransitionEffect(
                TimeContributionStateMachine.succeed, self.participant.contributions.get()
            )

            self.assertNotificationEffect(ActivitySucceededNotification)

            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_deadline_succeed_registration_deadline_passed(self):
        self.defaults['registration_deadline'] = date.today() - timedelta(days=5)

        self.test_submit()

        self.participant = self.participant_factory.create(activity=self.model)

        self.model.start = date.today() - timedelta(days=3)
        self.model.deadline = date.today() - timedelta(days=2)

        with self.execute():
            self.assertTransitionEffect(
                PeriodStateMachine.succeed
            )
            self.assertTransitionEffect(
                PeriodParticipantStateMachine.succeed, self.participant
            )

            self.assertTransitionEffect(
                TimeContributionStateMachine.succeed, self.participant.contributions.get()
            )

            self.assertNotificationEffect(ActivitySucceededNotification)

            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_deadline_reopen(self):
        self.test_change_deadline_expire()

        self.model = PeriodActivity.objects.get(pk=self.model.pk)

        self.model.start = date.today() + timedelta(days=3)
        self.model.deadline = date.today() + timedelta(days=10)

        with self.execute():
            self.assertTransitionEffect(
                PeriodStateMachine.reschedule
            )
            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_reopen_manually(self):
        self.test_change_deadline_expire()

        self.model = PeriodActivity.objects.get(pk=self.model.pk)

        self.model.states.reopen_manually()

        with self.execute():
            self.assertEffect(ClearDeadlineEffect)

    def test_change_deadline_reopen_succeeded(self):
        self.test_change_deadline_succeed()

        self.model = PeriodActivity.objects.get(pk=self.model.pk)

        self.model.start = date.today() + timedelta(days=3)
        self.model.deadline = date.today() + timedelta(days=10)

        with self.execute():
            self.assertTransitionEffect(
                PeriodStateMachine.reschedule
            )

            self.assertTransitionEffect(
                PeriodParticipantStateMachine.reaccept,
                self.participant
            )

            self.assertNotificationEffect(DeadlineChangedNotification)
            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_deadline_reopen_succeeded_full(self):
        self.defaults['capacity'] = 1
        self.test_change_deadline_succeed()

        self.model = PeriodActivity.objects.get(pk=self.model.pk)

        self.model.start = date.today() + timedelta(days=3)
        self.model.deadline = date.today() + timedelta(days=10)

        with self.execute():
            self.assertTransitionEffect(
                PeriodStateMachine.reschedule
            )

            self.assertTransitionEffect(
                PeriodStateMachine.lock
            )

            self.assertTransitionEffect(
                PeriodParticipantStateMachine.reaccept,
                self.participant
            )

            self.assertNotificationEffect(DeadlineChangedNotification)
            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_change_deadline_reopen_registration_deadline_passed(self):
        self.defaults['registration_deadline'] = date.today() - timedelta(days=5)
        self.test_change_deadline_succeed()

        self.model = PeriodActivity.objects.get(pk=self.model.pk)

        self.model.start = date.today() + timedelta(days=3)
        self.model.deadline = date.today() + timedelta(days=10)

        with self.execute():
            self.assertTransitionEffect(
                PeriodStateMachine.reschedule
            )

            self.assertTransitionEffect(
                PeriodStateMachine.lock
            )

            self.assertTransitionEffect(
                PeriodParticipantStateMachine.reaccept,
                self.participant
            )

            self.assertNotificationEffect(DeadlineChangedNotification)
            self.assertEffect(RescheduleOverallPeriodActivityDurationsEffect)

    def test_succeed_manually(self):
        self.defaults['start'] = None
        self.defaults['deadline'] = None

        self.test_submit()

        participant = self.participant_factory.create(activity=self.model)

        self.model.states.succeed_manually()

        with self.execute():
            self.assertTransitionEffect(
                PeriodParticipantStateMachine.succeed,
                participant
            )

            self.assertNotificationEffect(ActivitySucceededManuallyNotification)
            self.assertEffect(SetEndDateEffect)


class ParticipantTriggerTestCase():
    def setUp(self):
        self.activity = self.activity_factory.create()
        self.activity.initiative.states.submit()
        self.activity.initiative.states.approve(save=True)
        self.activity.states.submit(save=True)

        self.defaults = {
            'activity': self.activity,
            'user': BlueBottleUserFactory.create()
        }

        super().setUp()

    def test_initiate_user(self):
        self.build()

        with self.execute(user=self.model.user):
            self.assertEffect(CreatePeriodTimeContributionEffect)
            self.assertEffect(CreatePreparationTimeContributionEffect)
            self.assertTransitionEffect(PeriodParticipantStateMachine.accept)
            self.assertEffect(FollowActivityEffect)
            self.assertNotificationEffect(NewParticipantNotification)


    def test_initiate_user_full(self):
        self.activity.capacity = 1
        self.activity.save()
        self.build()

        with self.execute(user=self.model.user):
            self.assertEffect(CreatePeriodTimeContributionEffect)
            self.assertEffect(CreatePreparationTimeContributionEffect)
            self.assertTransitionEffect(PeriodParticipantStateMachine.accept)
            self.assertTransitionEffect(PeriodStateMachine.lock, self.activity)
            self.assertEffect(FollowActivityEffect)
            self.assertNotificationEffect(NewParticipantNotification)

    def test_initiate_user_review(self):
        self.activity.review = True
        self.activity.save()
        self.build()

        with self.execute(user=self.model.user):
            self.assertEffect(CreatePeriodTimeContributionEffect)
            self.assertEffect(CreatePreparationTimeContributionEffect)
            self.assertNoTransitionEffect(PeriodParticipantStateMachine.accept)
            self.assertEffect(FollowActivityEffect)

    def test_initiate_add(self):
        self.build()

        with self.execute():
            self.assertEffect(CreatePeriodTimeContributionEffect)
            self.assertEffect(FollowActivityEffect)
            self.assertEffect(CreatePreparationTimeContributionEffect)
            self.assertNotificationEffect(ParticipantAddedNotification)
            self.assertNotificationEffect(ParticipantAddedOwnerNotification)
            self.assertTransitionEffect(PeriodParticipantStateMachine.add)

    def test_initiate_add_review(self):
        self.activity.review = False
        self.build()

        with self.execute():
            self.assertEffect(CreatePeriodTimeContributionEffect)
            self.assertEffect(FollowActivityEffect)
            self.assertEffect(CreatePreparationTimeContributionEffect)
            self.assertNotificationEffect(ParticipantAddedNotification)
            self.assertNotificationEffect(ParticipantAddedOwnerNotification)
            self.assertTransitionEffect(PeriodParticipantStateMachine.add)

    def test_initiate_add_full(self):
        self.activity.capacity = 1
        self.activity.save()
        self.build()

        with self.execute():
            self.assertEffect(CreatePeriodTimeContributionEffect)
            self.assertEffect(FollowActivityEffect)
            self.assertEffect(CreatePreparationTimeContributionEffect)
            self.assertNotificationEffect(ParticipantAddedNotification)
            self.assertNotificationEffect(ParticipantAddedOwnerNotification)
            self.assertTransitionEffect(PeriodParticipantStateMachine.add)
            self.assertTransitionEffect(PeriodStateMachine.lock, self.activity)

    def test_accept(self):
        self.test_initiate_user_review()
        self.model.states.accept()

        with self.execute():
            self.assertNotificationEffect(ParticipantAcceptedNotification)

    def test_accept_full(self):
        self.activity.capacity = 1
        self.activity.save()
        self.test_initiate_user_review()
        self.model.states.accept()

        with self.execute():
            self.assertNotificationEffect(ParticipantAcceptedNotification)
            self.assertTransitionEffect(PeriodStateMachine.lock, self.activity)


class PeriodParticipantTriggerTestCase(ParticipantTriggerTestCase, TriggerTestCase):
    factory = PeriodParticipantFactory
    activity_factory = PeriodActivityFactory

    def test_add_finished(self):
        self.activity.start = date.today() - timedelta(days=2)
        self.activity.deadline = date.today() - timedelta(days=1)
        self.activity.save()

        self.build()

        with self.execute():
            self.assertEffect(CreatePeriodTimeContributionEffect)
            self.assertEffect(FollowActivityEffect)
            self.assertEffect(CreatePreparationTimeContributionEffect)
            self.assertNotificationEffect(ParticipantAddedNotification)
            self.assertNotificationEffect(ParticipantAddedOwnerNotification)
            self.assertTransitionEffect(PeriodParticipantStateMachine.add)

            self.assertTransitionEffect(PeriodStateMachine.succeed, self.activity)
            self.assertTransitionEffect(PeriodParticipantStateMachine.succeed)

    def test_initiate_finished(self):
        self.activity.start = date.today() - timedelta(days=2)
        self.activity.deadline = date.today() - timedelta(days=1)
        self.activity.save()

        self.build()

        with self.execute(user=self.model.user):
            self.assertTransitionEffect(PeriodStateMachine.succeed, self.activity)
            self.assertTransitionEffect(PeriodParticipantStateMachine.succeed)

    def test_initiate_finished_full(self):
        self.activity.start = date.today() - timedelta(days=2)
        self.activity.deadline = date.today() - timedelta(days=1)
        self.activity.capacity = 1
        self.activity.save()

        self.build()

        with self.execute(user=self.model.user):
            self.assertTransitionEffect(PeriodStateMachine.succeed, self.activity)
            self.assertTransitionEffect(PeriodParticipantStateMachine.succeed)


class DateSlotTriggersTestCase(TriggerTestCase):
    factory = DateActivitySlotFactory

    def setUp(self):
        self.owner = BlueBottleUserFactory.create()
        self.staff_user = BlueBottleUserFactory.create(is_staff=True)

        initiative = InitiativeFactory.create()
        initiative.states.submit()
        initiative.states.approve(save=True)

        self.activity = DateActivityFactory.create(
            initiative=initiative,
            slot_selection='all',
            owner=self.owner,
            slots=[]
        )

        self.defaults = {
            'activity': self.activity,
            'location': GeolocationFactory.create(),
            'start': now().replace(
                microsecond=0, second=0, minute=0, hour=12
            ) + timedelta(days=10),
            'is_online': True,
            'duration': timedelta(hours=2),
        }

        super().setUp()

    def test_initiate_incomplete(self):
        self.defaults['is_online'] = None
        self.build()

        with self.execute():
            self.assertNoTransitionEffect(DateActivitySlotStateMachine.mark_complete)
            self.assertEffect(
                CreateSlotParticipantsForSlotsEffect
            )

    def test_initiate_complete(self):
        self.build()

        with self.execute():
            self.assertTransitionEffect(DateActivitySlotStateMachine.mark_complete)
            self.assertEffect(
                CreateSlotParticipantsForSlotsEffect
            )

    def test_complete(self):
        self.defaults['is_online'] = None
        self.create()

        self.model.is_online = True

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.mark_complete
            )

    def test_complete_expired(self):
        self.defaults['is_online'] = None
        self.factory.create(activity=self.activity, start=now() - timedelta(days=7))
        self.activity.states.submit(save=True)
        self.create()

        self.model.is_online = True

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.mark_complete
            )

            self.assertTransitionEffect(
                DateStateMachine.reschedule,
                self.activity
            )

    def test_complete_succeeded(self):
        self.defaults['is_online'] = None
        self.factory.create(activity=self.activity, start=now() - timedelta(days=7))
        participant = DateParticipantFactory.create(activity=self.activity)
        self.activity.states.submit(save=True)
        self.create()

        self.model.is_online = True

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.mark_complete
            )

            self.assertTransitionEffect(
                DateStateMachine.reschedule,
                self.activity
            )

            self.assertTransitionEffect(
                DateParticipantStateMachine.reaccept,
                participant
            )

    def test_complete_full(self):
        self.defaults['is_online'] = None
        self.activity.capacity = 1
        self.factory.create(activity=self.activity)
        self.activity.states.submit(save=True)
        DateParticipantFactory.create(activity=self.activity)
        self.create()

        self.model.is_online = True

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.mark_complete
            )

            self.assertTransitionEffect(
                DateStateMachine.reopen,
                self.activity
            )

    def test_finish_no_participants(self):
        self.create()

        self.activity.states.submit(save=True)

        self.model.start = now() - timedelta(days=1)

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.finish
            )

            self.assertTransitionEffect(
                DateStateMachine.expire,
                self.activity
            )

    def test_finish_with_participant(self):
        self.create()
        self.activity.states.submit(save=True)

        self.participant = DateParticipantFactory.create(activity=self.activity)

        self.model.start = now() - timedelta(days=1)

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.finish
            )

            self.assertTransitionEffect(
                DateStateMachine.succeed,
                self.activity
            )

            self.assertEffect(
                ActiveTimeContributionsTransitionEffect(TimeContributionStateMachine.succeed)
            )

            self.assertTransitionEffect(
                DateParticipantStateMachine.succeed,
                self.participant
            )

    def test_finish_with_participant_multiple_slots(self):
        self.create()
        self.activity.states.submit(save=True)

        DateActivitySlotFactory.create(activity=self.activity)

        participant = DateParticipantFactory.create(activity=self.activity)

        self.model.start = now() - timedelta(days=1)

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.finish
            )

            self.assertNoTransitionEffect(
                DateStateMachine.succeed,
                self.activity
            )

            self.assertEffect(
                ActiveTimeContributionsTransitionEffect(TimeContributionStateMachine.succeed)
            )

            self.assertNoTransitionEffect(
                DateParticipantStateMachine.succeed,
                participant
            )

    def test_restart_with_participant(self):
        self.test_finish_with_participant()
        self.model.start = now() + timedelta(days=1)

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.reschedule
            )

            self.assertTransitionEffect(
                DateStateMachine.reschedule,
                self.activity
            )

            self.assertEffect(
                RescheduleSlotDurationsEffect
            )

            self.assertTransitionEffect(
                DateParticipantStateMachine.reaccept,
                self.participant
            )

    def test_restart_with_participants_full(self):
        self.defaults['capacity'] = 1
        self.create()

        self.activity.slot_selection = 'free'
        self.activity.states.submit(save=True)

        participant = DateParticipantFactory.create(activity=self.activity)
        SlotParticipantFactory.create(
            participant=participant,
            slot=self.model
        )
        self.model.start = now() - timedelta(days=1)

        self.model.save()

        self.model.start = now() + timedelta(days=1)

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.reschedule
            )

            self.assertTransitionEffect(
                DateActivitySlotStateMachine.lock
            )

            self.assertTransitionEffect(
                DateStateMachine.reschedule,
                self.activity
            )

            self.assertTransitionEffect(
                DateStateMachine.lock,
                self.activity
            )

            self.assertEffect(
                RescheduleSlotDurationsEffect
            )

            self.assertTransitionEffect(
                DateParticipantStateMachine.reaccept,
                participant
            )

    def test_change_capacity_lock(self):
        self.activity.slot_selection = 'free'
        self.activity.save()

        self.create()
        self.activity.states.submit(save=True)

        participant = DateParticipantFactory.create(activity=self.activity)
        SlotParticipantFactory.create(
            participant=participant,
            slot=self.model
        )

        self.model.capacity = 1

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.lock
            )

            self.assertTransitionEffect(
                DateStateMachine.lock,
                self.activity
            )

    def test_change_capacity_unlock(self):
        self.test_change_capacity_lock()

        self.model.capacity = 2

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.unlock
            )

            self.assertTransitionEffect(
                DateStateMachine.unlock,
                self.activity
            )

    def test_change_capacity_lock_multiple_slots(self):
        self.activity.slot_selection = 'free'
        self.activity.save()

        self.create()
        self.activity.states.submit(save=True)

        DateActivitySlotFactory.create(activity=self.activity)

        participant = DateParticipantFactory.create(activity=self.activity)
        SlotParticipantFactory.create(
            participant=participant,
            slot=self.model
        )

        self.model.capacity = 1

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.lock
            )

            self.assertNoTransitionEffect(
                DateStateMachine.lock,
                self.activity
            )

    def test_change_capacity_unlock_multiple_slots(self):
        self.test_change_capacity_lock_multiple_slots()

        self.model.capacity = 2

        with self.execute():
            self.assertTransitionEffect(
                DateActivitySlotStateMachine.unlock
            )

            self.assertNoTransitionEffect(
                DateStateMachine.unlock,
                self.activity
            )

    def test_change_duration(self):
        self.create()

        self.model.duration = timedelta(hours=3)

        with self.execute():
            self.assertEffect(RescheduleSlotDurationsEffect)

    def test_cancel(self):
        self.create()
        self.activity.states.submit(save=True)
        DateParticipantFactory.create(activity=self.activity)

        self.model.states.cancel()

        with self.execute():
            self.assertEffect(
                ActiveTimeContributionsTransitionEffect(TimeContributionStateMachine.fail)
            )

            self.assertTransitionEffect(
                DateStateMachine.cancel,
                self.activity
            )

    def test_cancel_multiple_slots(self):
        self.create()
        self.activity.states.submit(save=True)
        DateParticipantFactory.create(activity=self.activity)

        DateActivitySlotFactory.create(activity=self.activity)

        self.model.states.cancel()

        with self.execute():
            self.assertEffect(
                ActiveTimeContributionsTransitionEffect(TimeContributionStateMachine.fail)
            )

            self.assertNoTransitionEffect(
                DateStateMachine.cancel,
                self.activity
            )

