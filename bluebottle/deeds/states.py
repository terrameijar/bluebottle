from django.utils.translation import ugettext_lazy as _

from bluebottle.activities.states import ActivityStateMachine, ContributorStateMachine
from bluebottle.deeds.models import Deed, DeedParticipant
from bluebottle.fsm.state import register, State, Transition, EmptyState


@register(Deed)
class DeedStateMachine(ActivityStateMachine):
    running = State(
        _('running'),
        'running',
        _('The activity is currently taking place.')
    )

    def has_no_end_date(self):
        return self.instance.end is None

    start = Transition(
        [
            ActivityStateMachine.open,
            ActivityStateMachine.succeeded,
        ],
        running,
        name=_("Start"),
        description=_("Start the activity.")
    )

    succeed = Transition(
        [ActivityStateMachine.open, running],
        ActivityStateMachine.succeeded,
        name=_('Succeed'),
        automatic=True,
    )

    expire = Transition(
        [
            ActivityStateMachine.open, ActivityStateMachine.submitted,
            ActivityStateMachine.succeeded, running
        ],
        ActivityStateMachine.expired,
        name=_('Expire'),
        description=_(
            "The activity will be cancelled because no one has signed up for the registration deadline."
        ),
        automatic=True,
    )

    succeed_manually = Transition(
        [
            ActivityStateMachine.open,
            running
        ],
        ActivityStateMachine.succeeded,
        automatic=False,
        name=_("succeed"),
        hide_from_admin=True,
        conditions=[has_no_end_date],
        permission=ActivityStateMachine.is_owner,
        description=_("Succeed the activity.")
    )

    restart = Transition(
        [
            ActivityStateMachine.expired,
            ActivityStateMachine.succeeded,
        ],
        running,
        name=_("Start"),
        description=_("Restart the activity.")
    )

    reopen = Transition(
        [
            running,
            ActivityStateMachine.expired,
            ActivityStateMachine.succeeded,
        ],
        ActivityStateMachine.open,
        name=_("Reopen"),
        description=_("Reopen the activity.")
    )

    reopen_manually = Transition(
        [ActivityStateMachine.succeeded, ActivityStateMachine.expired],
        ActivityStateMachine.draft,
        name=_("Reopen"),
        permission=ActivityStateMachine.is_owner,
        automatic=False,
        description=_(
            "Manually reopen the activity. "
            "This will unset the end date if the date is in the past. "
            "People can sign up again for the task."
        )
    )

    cancel = Transition(
        [
            ActivityStateMachine.open,
            ActivityStateMachine.succeeded,
            running
        ],
        ActivityStateMachine.cancelled,
        name=_('Cancel'),
        permission=ActivityStateMachine.is_owner,
        description=_(
            'Cancel if the activity will not be executed. '
            'The activity manager can no longer edit the activity '
            'and it will no longer be visible on the platform. '
            'The activity will still be visible in the back office '
            'and will continue to count in the reporting.'
        ),
        automatic=False,
        hide_from_admin=True,
    )


@register(DeedParticipant)
class DeedParticipantStateMachine(ContributorStateMachine):
    withdrawn = State(
        _('withdrawn'),
        'withdrawn',
        _('This person has withdrawn.')
    )
    rejected = State(
        _('Removed'),
        'rejected',
        _('This person has been removed from the activity.')
    )
    accepted = State(
        _('Participating'),
        'accepted',
        _('This person has been signed up for the activity and was accepted automatically.')
    )

    def is_user(self, user):
        """is participant"""
        return self.instance.user == user or user.is_staff

    def is_owner(self, user):
        """is participant"""
        return self.instance.activity.owner == user or user.is_staff

    def activity_is_open(self):
        """task is open"""
        return self.instance.activity.status in (
            DeedStateMachine.open.value,
            DeedStateMachine.running.value,
        )

    initiate = Transition(
        EmptyState(),
        accepted,
        name=_('initiate'),
        description=_('The contribution was created.')
    )

    succeed = Transition(
        ContributorStateMachine.new,
        ContributorStateMachine.succeeded,
        name=_('Succeed'),
        automatic=True,
    )

    withdraw = Transition(
        accepted,
        withdrawn,
        name=_('Withdraw'),
        description=_("Stop your participation in the activity."),
        automatic=False,
        permission=is_user,
        hide_from_admin=True,
    )

    reapply = Transition(
        withdrawn,
        accepted,
        name=_('Reapply'),
        description=_("User re-applies after previously withdrawing."),
        automatic=False,
        conditions=[activity_is_open],
        permission=is_user,
    )

    remove = Transition(
        [
            accepted,
            ContributorStateMachine.succeeded
        ],
        rejected,
        name=_('Remove'),
        description=_("Rmove participant from the activity."),
        automatic=False,
        permission=is_owner,
        hide_from_admin=True,
    )

    accept = Transition(
        rejected,
        ContributorStateMachine.new,
        name=_('Re-Accept'),
        description=_("User is re-accepted after previously withdrawing."),
        automatic=False,
        permission=is_owner,
    )
