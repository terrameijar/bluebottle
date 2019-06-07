import factory.fuzzy

from bluebottle.funding.models import Funding
from bluebottle.initiatives.tests.factories import InitiativeFactory
from bluebottle.test.factory_models.accounts import BlueBottleUserFactory


class FundingFactory(factory.DjangoModelFactory):

    class Meta(object):
        model = Funding

    title = factory.Faker('sentence')
    description = factory.Faker('text')

    owner = factory.SubFactory(BlueBottleUserFactory)
    initiative = factory.SubFactory(InitiativeFactory)
