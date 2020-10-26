from datetime import timedelta
from django.utils.timezone import now

from bluebottle.fsm.triggers import register, ModelChangedTrigger, TransitionTrigger
from bluebottle.fsm.effects import TransitionEffect, RelatedTransitionEffect
from bluebottle.notifications.effects import NotificationEffect

from bluebottle.activities.triggers import ActivityTriggers, ContributionTriggers

from bluebottle.time_based.models import (
    OnADateActivity, WithADeadlineActivity, OngoingActivity, Application
)
from bluebottle.time_based.messages import DateChanged, DeadlineChanged
from bluebottle.time_based.states import (
    TimeBasedStateMachine, OnADateStateMachine, WithADeadlineStateMachine,
    ApplicationStateMachine
)


def is_full(effect):
    "the activity is full"
    return effect.instance.capacity <= len(effect.instance.accepted_applications)


def is_not_full(effect):
    "the activity is not full"
    return effect.instance.capacity > len(effect.instance.accepted_applications)


def has_applications(effect):
    return len(effect.instance.accepted_applications) > 0


def has_no_applications(effect):
    return len(effect.instance.accepted_applications) == 0


def is_finished(effect):
    return (
        effect.instance.start and
        effect.instance.duration and
        effect.instance.start + timedelta(hours=effect.instance.duration) < now()
    )


def is_not_finished(effect):
    return (
        effect.instance.start and
        effect.instance.duration and
        effect.instance.start + timedelta(hours=effect.instance.duration) > now()
    )


def registration_deadline_is_passed(effect):
    return (
        effect.instance.registration_deadline and
        effect.instance.registration_deadline < now().date()
    )


def registration_deadline_is_not_passed(effect):
    return (
        effect.instance.registration_deadline and
        effect.instance.registration_deadline > now().date()
    )


def deadline_is_passed(effect):
    return (
        effect.instance.deadline and
        effect.instance.deadline < now()
    )


def deadline_is_not_passed(effect):
    return (
        effect.instance.deadline and
        effect.instance.deadline > now()
    )


def is_started(effect):
    return (
        effect.instance.start and
        effect.instance.start < now().date()
    )


def is_not_started(effect):
    return (
        effect.instance.start and
        effect.instance.start > now().date()
    )


class TimeBasedTriggers(ActivityTriggers):
    triggers = ActivityTriggers.triggers + [
        ModelChangedTrigger(
            'capacity',
            effects=[
                TransitionEffect(TimeBasedStateMachine.reopen, conditions=[
                    is_not_full
                ]),
                TransitionEffect(TimeBasedStateMachine.lock, conditions=[
                    is_full
                ]),
            ]
        ),

        ModelChangedTrigger(
            'registration_deadline',
            effects=[
                TransitionEffect(TimeBasedStateMachine.lock, conditions=[
                    registration_deadline_is_passed
                ]),
                TransitionEffect(TimeBasedStateMachine.reopen, conditions=[
                    registration_deadline_is_not_passed
                ]),
            ]
        ),
    ]


@ register(OnADateActivity)
class OnADateTriggers(TimeBasedTriggers):
    triggers = TimeBasedTriggers.triggers + [
        TransitionTrigger(
            OnADateStateMachine.reschedule,
            effects=[
                TransitionEffect(TimeBasedStateMachine.lock, conditions=[is_full]),
            ]
        ),
        ModelChangedTrigger(
            'start',
            effects=[
                NotificationEffect(
                    DateChanged,
                    conditions=[
                        is_not_finished
                    ]
                ),
                TransitionEffect(
                    OnADateStateMachine.succeed,
                    conditions=[
                        is_finished, has_applications
                    ]
                ),
                TransitionEffect(
                    OnADateStateMachine.expire,
                    conditions=[
                        is_finished, has_no_applications
                    ]
                ),
                TransitionEffect(
                    OnADateStateMachine.reschedule,
                    conditions=[
                        is_not_finished
                    ]
                ),
            ]
        )
    ]


@ register(WithADeadlineActivity)
class WithADeadlineTriggers(TimeBasedTriggers):

    triggers = TimeBasedTriggers.triggers + [
        TransitionTrigger(
            WithADeadlineStateMachine.reschedule,
            effects=[
                TransitionEffect(TimeBasedStateMachine.lock, conditions=[is_full]),
                TransitionEffect(
                    TimeBasedStateMachine.lock, conditions=[registration_deadline_is_passed]
                )
            ]
        ),

        ModelChangedTrigger(
            'start',
            effects=[
                TransitionEffect(
                    OnADateStateMachine.start,
                    conditions=[is_started]
                ),

                TransitionEffect(
                    OnADateStateMachine.reopen,
                    conditions=[is_not_started, is_not_full]
                ),

                TransitionEffect(
                    OnADateStateMachine.lock,
                    conditions=[is_not_started, is_full]
                ),

                TransitionEffect(
                    TimeBasedStateMachine.lock,
                    conditions=[is_not_started, registration_deadline_is_passed]
                )
            ]
        ),
        ModelChangedTrigger(
            'deadline',
            effects=[
                NotificationEffect(
                    DeadlineChanged,
                    conditions=[
                        deadline_is_not_passed
                    ]
                ),
                TransitionEffect(
                    OnADateStateMachine.succeed,
                    conditions=[
                        deadline_is_passed, has_applications
                    ]
                ),
                TransitionEffect(
                    OnADateStateMachine.expire,
                    conditions=[
                        deadline_is_passed, has_no_applications
                    ]
                ),
                TransitionEffect(
                    WithADeadlineStateMachine.reschedule,
                    conditions=[
                        deadline_is_not_passed
                    ]
                ),
            ]
        )
    ]


@ register(OngoingActivity)
class OngoingTriggers(TimeBasedTriggers):
    pass


def automatically_accept(effect):
    return not effect.instance.activity.review


def activity_will_be_full(effect):
    "the activity is full"
    activity = effect.instance.activity
    return activity.capacity == len(activity.accepted_applications) + 1


def activity_will_not_be_full(effect):
    "the activity is full"
    activity = effect.instance.activity
    return activity.capacity >= len(activity.accepted_applications)


def activity_is_finished(effect):
    activity = effect.instance.activity

    if isinstance(activity, OnADateActivity):
        return (
            activity.start and
            activity.duration and
            activity.start + timedelta(hours=activity.duration) < now()
        )
    elif isinstance(activity, WithADeadlineActivity):
        return (
            activity.deadline and
            activity.deadline < now()
        )
    else:
        return False


@ register(Application)
class ApplicationTriggers(ContributionTriggers):
    triggers = ContributionTriggers.triggers + [
        TransitionTrigger(
            ApplicationStateMachine.initiate,
            effects=[
                TransitionEffect(
                    ApplicationStateMachine.accept,
                    conditions=[automatically_accept]
                ),

            ]
        ),

        TransitionTrigger(
            ApplicationStateMachine.reapply,
            effects=[
                TransitionEffect(
                    ApplicationStateMachine.accept,
                    conditions=[automatically_accept]
                )
            ]
        ),

        TransitionTrigger(
            ApplicationStateMachine.accept,
            effects=[
                RelatedTransitionEffect(
                    'activity',
                    TimeBasedStateMachine.lock,
                    conditions=[activity_will_be_full]
                ),

                RelatedTransitionEffect(
                    'activity',
                    TimeBasedStateMachine.succeed,
                    conditions=[activity_is_finished]
                )
            ]
        ),

        TransitionTrigger(
            ApplicationStateMachine.reject,
            effects=[
                RelatedTransitionEffect(
                    'activity',
                    TimeBasedStateMachine.reopen,
                    conditions=[activity_will_not_be_full]
                )
            ]
        ),

        TransitionTrigger(
            ApplicationStateMachine.withdraw,
            effects=[
                RelatedTransitionEffect(
                    'activity',
                    TimeBasedStateMachine.reopen,
                    conditions=[activity_will_not_be_full]
                )
            ]
        ),
    ]
