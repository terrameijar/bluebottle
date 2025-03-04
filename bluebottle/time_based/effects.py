from datetime import datetime, date

from dateutil.relativedelta import relativedelta
from django.db.models import F
from django.template.loader import render_to_string
from django.utils.timezone import get_current_timezone, now
from django.utils.translation import gettext as _

from bluebottle.fsm.effects import Effect
from bluebottle.time_based.models import TimeContribution, SlotParticipant, ContributionTypeChoices


class CreateSlotTimeContributionEffect(Effect):
    title = _('Create contribution')
    template = 'admin/create_slot_time_contribution.html'

    def post_save(self, **kwargs):
        slot = self.instance.slot
        if slot.start and slot.duration:
            end = slot.start + slot.duration
            contribution = TimeContribution(
                contributor=self.instance.participant,
                contribution_type=ContributionTypeChoices.date,
                slot_participant=self.instance,
                value=slot.duration,
                start=slot.start,
                end=end
            )
            contribution.save()


class CreatePreparationTimeContributionEffect(Effect):
    title = _('Create preparation time contribution')
    template = 'admin/create_preparation_time_contribution.html'

    def post_save(self, **kwargs):
        activity = self.instance.activity
        if activity.preparation:
            start = now()
            contribution = TimeContribution(
                contributor=self.instance,
                contribution_type=ContributionTypeChoices.preparation,
                value=activity.preparation,
                start=start,
            )
            contribution.save()


class CreateOverallTimeContributionEffect(Effect):
    title = _('Create contribution')
    template = 'admin/create_period_time_contribution.html'

    def post_save(self, **kwargs):
        tz = get_current_timezone()
        activity = self.instance.activity

        # Just create a contribution for the full period
        start = activity.start or date.today()
        end = activity.deadline if hasattr(activity, 'deadline') else None

        TimeContribution.objects.create(
            contributor=self.instance,
            contribution_type=ContributionTypeChoices.period,
            value=activity.duration,
            start=tz.localize(datetime.combine(start, datetime.min.time())),
            end=tz.localize(datetime.combine(end, datetime.min.time())) if end else None,
        )

    def __str__(self):
        return _('Create overall contribution')

    @property
    def is_valid(self):
        return super().is_valid and self.instance.activity.duration_period == 'overall'


class CreatePeriodTimeContributionEffect(Effect):
    title = _('Create contribution')
    template = 'admin/create_period_time_contribution.html'

    def post_save(self, **kwargs):
        tz = get_current_timezone()
        activity = self.instance.activity

        if self.instance.current_period or not activity.start:
            # Use today if we already have previous contributions
            # or when we create a new contribution and now start
            start = date.today()
        else:
            # The first contribution should start on the start
            start = activity.start

        # Calculate the next end
        end = start + relativedelta(**{activity.duration_period: 1})
        if activity.deadline and end > activity.deadline:
            # the end is passed the deadline
            end = activity.deadline

        # Update the current_period
        self.instance.current_period = end
        self.instance.save()

        if not activity.deadline or start < activity.deadline:
            # Only when the deadline is not passed, create the new contribution
            TimeContribution.objects.create(
                contributor=self.instance,
                contribution_type=ContributionTypeChoices.period,
                value=activity.duration,
                start=tz.localize(datetime.combine(start, datetime.min.time())),
                end=tz.localize(datetime.combine(end, datetime.min.time())) if end else None,
            )

    def __str__(self):
        return _('Create contribution')

    @property
    def is_valid(self):
        return super().is_valid and self.instance.activity.duration_period != 'overall'


class SetEndDateEffect(Effect):
    title = _('End the activity')
    template = 'admin/set_end_date.html'

    def pre_save(self, **kwargs):
        self.instance.deadline = date.today()


class ClearDeadlineEffect(Effect):
    title = _('Clear the deadline of the activity')
    template = 'admin/clear_deadline.html'

    def pre_save(self, **kwargs):
        self.instance.deadline = None


class RescheduleOverallPeriodActivityDurationsEffect(Effect):
    display = False

    def post_save(self, **kwargs):
        if self.instance.duration_period == 'overall':
            tz = get_current_timezone()

            if self.instance.start:
                start = tz.localize(datetime.combine(self.instance.start, datetime.min.time()))
            else:
                start = F('start')

            if self.instance.deadline:
                end = tz.localize(datetime.combine(self.instance.deadline, datetime.min.time()))
            else:
                end = None

            self.instance.durations.update(
                start=start,
                end=end,
                value=self.instance.duration
            )


class RescheduleSlotDurationsEffect(Effect):
    display = False

    def post_save(self, **kwargs):
        if self.instance.start and self.instance.duration:
            self.instance.durations.update(
                start=self.instance.start,
                end=self.instance.start + self.instance.duration,
                value=self.instance.duration
            )


class BaseActiveDurationsTransitionEffect(Effect):
    display = True
    template = 'admin/transition_durations.html'

    @classmethod
    def render(cls, effects):
        effect = effects[0]
        users = [duration.contributor.user for duration in effect.instance.active_durations]
        context = {
            'users': users,
            'transition': cls.transition.name
        }
        return render_to_string(cls.template, context)

    @property
    def is_valid(self):
        return (
            super().is_valid and
            any(
                self.transition in duration.states.possible_transitions() for
                duration in self.instance.active_durations
            )
        )

    def pre_save(self, effects):
        self.transitioned_durations = []
        for duration in self.instance.active_durations:
            if self.transition in duration.states.possible_transitions():
                self.transitioned_durations.append(duration)
                self.transition.execute(duration.states)

    def post_save(self):
        for duration in self.transitioned_durations:
            duration.save()


def ActiveTimeContributionsTransitionEffect(transition, conditions=None):
    _transition = transition
    _conditions = conditions or []

    class _ActiveDurationsTransitionEffect(BaseActiveDurationsTransitionEffect):
        transition = _transition
        conditions = _conditions

    return _ActiveDurationsTransitionEffect


class CreateSlotParticipantsForSlotsEffect(Effect):
    title = _('Add participants to all slots if slot selection is set to "all"')
    template = 'admin/create_slot_participants_for_slot.html'

    @property
    def display(self):
        return self.instance.activity.slot_selection == 'all' \
            and self.instance.activity.active_participants.count()

    def post_save(self, **kwargs):
        slot = self.instance
        activity = self.instance.activity
        if activity.slot_selection == 'all':
            for participant in activity.accepted_participants:
                SlotParticipant.objects.create(participant=participant, slot=slot)


class CreateSlotParticipantsForParticipantsEffect(Effect):
    """
    Create register participants for all slots
    """
    title = _('Add participants to all slots if slot selection is set to "all"')
    template = 'admin/create_slot_participants_for_participant.html'

    @property
    def display(self):
        return self.instance.activity.slot_selection == 'all' \
            and self.instance.activity.slots.count()

    def post_save(self, **kwargs):
        participant = self.instance
        activity = self.instance.activity
        if activity.slot_selection == 'all':
            for slot in activity.slots.all():
                SlotParticipant.objects.create(participant=participant, slot=slot)


class UnlockUnfilledSlotsEffect(Effect):
    """
    Open up slots that are no longer full
    """

    template = 'admin/unlock_activity_slots.html'

    @property
    def display(self):
        return len(self.slots)

    @property
    def slots(self):
        if self.instance.activity.slot_selection == 'all':
            return []
        slots = self.instance.activity.slots.filter(status='full')
        return [slot for slot in slots.all() if slot.accepted_participants.count() < slot.capacity]

    def post_save(self, **kwargs):
        for slot in self.slots:
            slot.states.unlock(save=True)

    def __repr__(self):
        return '<Effect: Unlock unfilled slots for by {}>'.format(self.instance.activity)

    def __str__(self):
        return _('Unlock unfilled slots for {activity}').format(activity=self.instance.activity)


class LockFilledSlotsEffect(Effect):
    """
    Lock slots that will be full
    """

    template = 'admin/lock_activity_slots.html'

    @property
    def display(self):
        return len(self.slots)

    @property
    def slots(self):
        if self.instance.activity.slot_selection == 'all':
            return []
        slots = self.instance.activity.slots.filter(status='open')
        return [
            slot for slot in slots.all()
            if slot.capacity and slot.accepted_participants.count() >= slot.capacity
        ]

    def post_save(self, **kwargs):
        for slot in self.slots:
            slot.states.lock(save=True)

    def __repr__(self):
        return '<Effect: Lock filled slots for by {}>'.format(self.instance.activity)

    def __str__(self):
        return _('Lock filled slots for {activity}').format(activity=self.instance.activity)


class ResetSlotSelectionEffect(Effect):
    """
    Reset slot selection to 'all' when only 1 slot is left
    """

    template = 'admin/reset_slot_selection.html'

    def post_save(self):
        self.instance.activity.slot_selection = 'all'
        self.instance.activity.save()

    @property
    def is_valid(self):
        return (
            len(self.instance.activity.slots.all()) <= 2 and self.instance.activity.slot_selection == 'free'
        )

    def __repr__(self):
        return '<Effect: Reset slot selection to "all">'

    def __str__(self):
        return _('Reset slot selection to "all" for {activity}').format(activity=self.instance.activity)


class UnsetCapacityEffect(Effect):
    """
    Unset the capacity when slot selection becomes free
    """

    template = 'admin/unset_capacity.html'

    def pre_save(self, **kwargs):
        self.instance.capacity = None

    @property
    def is_valid(self):
        return self.instance.slot_selection == 'free' and self.instance.capacity

    def __repr__(self):
        return '<Effect: Unset the capacity>'

    def __str__(self):
        return _('Reset slot selection to "all" for {activity}').format(activity=self.instance)
