from datetime import timedelta
from unittest import mock

import stripe
from django.utils.timezone import now
from djmoney.money import Money

from bluebottle.funding.states import FundingStateMachine
from bluebottle.funding.tests.factories import FundingFactory, BudgetLineFactory, BankAccountFactory, \
    PlainPayoutAccountFactory, DonorFactory
from bluebottle.funding_pledge.tests.factories import PledgePaymentFactory
from bluebottle.funding_stripe.tests.factories import ExternalAccountFactory, StripePaymentFactory
from bluebottle.initiatives.tests.factories import InitiativeFactory
from bluebottle.test.utils import BluebottleTestCase


class FundingTriggerTests(BluebottleTestCase):
    def setUp(self):
        self.initiative = InitiativeFactory.create()
        self.initiative.states.submit()
        self.initiative.states.approve(save=True)
        self.funding = FundingFactory.create(
            initiative=self.initiative,
            target=Money(1000, 'EUR')
        )
        BudgetLineFactory.create(activity=self.funding)
        payout_account = PlainPayoutAccountFactory.create()
        bank_account = BankAccountFactory.create(connect_account=payout_account, status='verified')
        self.funding.bank_account = bank_account
        self.funding.states.submit(save=True)

    def test_trigger_matching(self):
        self.assertEqual(self.funding.status, FundingStateMachine.submitted.value)
        self.funding.states.approve(save=True)
        self.assertEqual(self.funding.status, FundingStateMachine.open.value)
        donation = DonorFactory.create(activity=self.funding, amount=Money(500, 'EUR'))
        PledgePaymentFactory.create(donation=donation)
        # Changing the deadline to the past should trigger a transition
        self.funding.deadline = now() - timedelta(days=1)
        self.funding.save()
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.status, FundingStateMachine.partially_funded.value)
        # Add amount matched funding to complete the project should transition it to succeeded
        self.funding.amount_matching = Money(500, 'EUR')
        self.funding.save()
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.status, FundingStateMachine.succeeded.value)

    def test_trigger_lower_target(self):
        self.assertEqual(self.funding.status, FundingStateMachine.submitted.value)
        self.funding.states.approve(save=True)
        self.assertEqual(self.funding.status, FundingStateMachine.open.value)
        donation = DonorFactory.create(activity=self.funding, amount=Money(500, 'EUR'))
        PledgePaymentFactory.create(donation=donation)
        # Changing the deadline to the past should trigger a transition
        self.funding.deadline = now() - timedelta(days=1)
        self.funding.save()
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.status, FundingStateMachine.partially_funded.value)
        # Lower target of the project should transition it to succeeded
        self.funding.target = Money(500, 'EUR')
        self.funding.save()
        self.funding.refresh_from_db()
        self.assertEqual(self.funding.status, FundingStateMachine.succeeded.value)


class DonorTriggerTests(BluebottleTestCase):
    def setUp(self):
        self.initiative = InitiativeFactory.create()
        self.initiative.states.submit()
        self.initiative.states.approve(save=True)
        self.funding = FundingFactory.create(
            initiative=self.initiative,
            deadline=now() + timedelta(days=10),
            target=Money(1000, 'EUR')
        )
        BudgetLineFactory.create(activity=self.funding)
        bank_account = ExternalAccountFactory.create(status='verified')
        self.funding.bank_account = bank_account
        self.funding.states.submit(save=True)
        self.funding.states.approve(save=True)
        self.donor = DonorFactory.create(activity=self.funding, amount=Money(500, 'EUR'))
        self.payment = StripePaymentFactory.create(donation=self.donor)
        self.payment.states.succeed(save=True)

    def test_change_donor_amount(self):
        self.assertEqual(self.donor.amount, Money(500, 'EUR'))
        self.assertEqual(self.donor.payout_amount, Money(500, 'EUR'))
        contribution = self.donor.contributions.get()
        self.assertEqual(contribution.value, Money(500, 'EUR'))
        self.assertEqual(self.funding.amount_donated, Money(500, 'EUR'))

        self.donor.amount = Money(200, 'EUR')
        self.donor.payout_amount = Money(200, 'EUR')
        self.donor.save()

        self.funding.refresh_from_db()
        self.assertEqual(self.donor.amount, Money(200, 'EUR'))
        self.assertEqual(self.donor.payout_amount, Money(200, 'EUR'))
        contribution = self.donor.contributions.get()
        self.assertEqual(contribution.value, Money(200, 'EUR'))
        self.assertEqual(self.funding.amount_donated, Money(200, 'EUR'))

        self.donor.payout_amount = Money(250, 'USD')
        self.donor.save()
        self.funding.refresh_from_db()
        self.assertEqual(self.donor.amount, Money(200, 'EUR'))
        self.assertEqual(self.donor.payout_amount, Money(250, 'USD'))
        contribution = self.donor.contributions.get()
        self.assertEqual(contribution.value, Money(250, 'USD'))
        self.assertEqual(self.funding.amount_donated, Money(200, 'EUR'))

    def test_donor_activity_refunded(self):
        """
        Test that donation ends up as activity_refund when refunding a funding activity
        """
        self.assertEqual(self.donor.amount, Money(500, 'EUR'))
        self.funding.deadline = now() - timedelta(days=1)
        self.funding.save()
        payment_intent = stripe.PaymentIntent('some intent id')

        charge = stripe.Charge('charge-id')
        charges = stripe.ListObject()
        charges.data = [charge]

        payment_intent.charges = charges

        with mock.patch(
            'stripe.PaymentIntent.retrieve', return_value=payment_intent
        ), mock.patch(
            'stripe.Charge.refund', return_value=payment_intent
        ):
            self.assertEqual(self.funding.status, 'partially_funded')
            self.funding.states.refund(save=True)
            self.donor.refresh_from_db()
            self.payment.states.refund(save=True)

        self.donor.refresh_from_db()
        self.assertEqual(self.donor.status, 'activity_refunded')
