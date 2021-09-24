from bluebottle.test.utils import BluebottleTestCase
from bluebottle.deeds.tests.factories import DeedParticipantFactory, DeedFactory
from bluebottle.impact.tests.factories import ImpactGoalFactory


class CreateEffortContributionTestCase(BluebottleTestCase):
    def setUp(self):
        self.activity = DeedFactory.create(target=10)
        self.activity.initiative.states.submit(save=True)
        self.activity.states.submit(save=True)
        self.activity.initiative.states.approve(save=True)

        participant = DeedParticipantFactory.create(activity=self.activity)
        self.contribution = participant.contributions.first()
        self.impact_goal = ImpactGoalFactory.create(
            activity=self.activity,
            target=100,
            realized=0,
        )

    def test_status_new(self):
        self.assertEqual(self.impact_goal.realized, 0)

    def test_status_succeed(self):
        self.contribution.states.succeed(save=True)
        self.impact_goal.refresh_from_db()

        self.assertEqual(self.impact_goal.realized, 1)

    def test_status_succeed_not_coupled(self):
        self.activity.target = None
        self.activity.save()

        self.contribution.states.succeed(save=True)
        self.impact_goal.refresh_from_db()

        self.assertEqual(self.impact_goal.realized, 0)

    def test_status_fail(self):
        self.test_status_succeed()
        self.contribution.states.fail(save=True)
        self.impact_goal.refresh_from_db()

        self.assertEqual(self.impact_goal.realized, 0)
