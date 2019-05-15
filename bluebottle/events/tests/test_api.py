import json
from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status

from bluebottle.initiatives.tests.factories import InitiativeFactory
from bluebottle.test.factory_models.accounts import BlueBottleUserFactory
from bluebottle.test.utils import BluebottleTestCase, JSONAPITestClient


class EventTestCase(BluebottleTestCase):

    def setUp(self):
        super(EventTestCase, self).setUp()
        self.client = JSONAPITestClient()
        self.url = reverse('event-list')
        self.user = BlueBottleUserFactory()
        self.initiative = InitiativeFactory(owner=self.user)

    def test_create_event(self):
        data = {
            'data': {
                'type': 'events',
                'attributes': {
                    'title': 'Beach clean-up Katwijk',
                    'start': str(now() + timedelta(days=21)),
                    'end': str(now() + timedelta(days=21, hours=4)),
                    'registration_deadline': str(now() + timedelta(days=14)),
                    'capacity': 10,
                    'address': 'Zuid-Boulevard Katwijk aan Zee',
                    'description': 'We will clean up the beach south of Katwijk'
                },
                'relationships': {
                    'initiative': {
                        'data': {
                            'type': 'initiatives', 'id': self.initiative.id
                        },
                    },
                }
            }
        }
        response = self.client.post(self.url, json.dumps(data), user=self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'open')
        self.assertEqual(response.data['title'], 'Beach clean-up Katwijk')

        # Add an event with the same title should return an error
        response = self.client.post(self.url, json.dumps(data), user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data['title'][0]), 'Activity with this title already exists.')

    def test_create_event_not_initiator(self):
        another_user = BlueBottleUserFactory.create()
        data = {
            'data': {
                'type': 'events',
                'attributes': {
                    'title': 'Beach clean-up Katwijk',
                    'start': str(now() + timedelta(days=21)),
                    'end': str(now() + timedelta(days=21, hours=4)),
                    'registration_deadline': str(now() + timedelta(days=14)),
                    'capacity': 10,
                    'address': 'Zuid-Boulevard Katwijk aan Zee',
                    'description': 'We will clean up the beach south of Katwijk'
                },
                'relationships': {
                    'initiative': {
                        'data': {
                            'type': 'initiatives', 'id': self.initiative.id
                        },
                    },
                }
            }
        }
        response = self.client.post(self.url, json.dumps(data), user=another_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
