from django.utils.translation import gettext as _
from django.contrib.contenttypes.models import ContentType

from bluebottle.fsm.effects import Effect
from bluebottle.impact.models import ImpactGoal
from bluebottle.activities.models import EffortContribution, Organizer


class UpdateImpactGoalEffect(Effect):
    title = _('Update impact goals')
    display = False

    def post_save(self, **kwargs):
        activity = self.instance.contributor.activity
        goals = ImpactGoal.objects.filter(activity=activity, coupled_with_contributions=True)

        for goal in goals:
            goal.realized = len(
                EffortContribution.objects.exclude(
                    contributor__polymorphic_ctype=ContentType.objects.get_for_model(Organizer)
                ).filter(
                    contributor__activity=activity,
                    status='succeeded',
                )
            )
            goal.save()
