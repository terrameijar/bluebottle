from django.contrib import admin

from bluebottle.funding.admin import PaymentChildAdmin, PaymentProviderChildAdmin, PayoutAccountChildAdmin, \
    BankAccountChildAdmin
from bluebottle.funding.models import BankAccount, Payment, PaymentProvider
from bluebottle.funding_stripe.models import StripePayment, StripePaymentProvider, StripePayoutAccount, \
    StripeSourcePayment, ExternalAccount


@admin.register(StripePayment)
class StripePaymentAdmin(PaymentChildAdmin):
    base_model = StripePayment


@admin.register(StripeSourcePayment)
class StripeSourcePaymentAdmin(PaymentChildAdmin):
    base_model = Payment


@admin.register(StripePaymentProvider)
class PledgePaymentProviderAdmin(PaymentProviderChildAdmin):
    base_model = PaymentProvider


class StripeBankAccountInline(admin.TabularInline):
    model = ExternalAccount
    readonly_fields = ['created', 'verified', 'account_id', ]
    fields = readonly_fields
    extra = 0
    can_delete = False


@admin.register(StripePayoutAccount)
class StripePayoutAccountAdmin(PayoutAccountChildAdmin):
    model = StripePayoutAccount
    inlines = [StripeBankAccountInline]

    fields = ('owner', 'status', 'account_id', 'country')


@admin.register(ExternalAccount)
class StripeBankAccountAdmin(BankAccountChildAdmin):
    base_model = BankAccount
    model = ExternalAccount
    fields = ('connect_account', 'account_id') + BankAccountChildAdmin.readonly_fields
