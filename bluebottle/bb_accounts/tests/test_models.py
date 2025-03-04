from django.core import mail
from django.db import IntegrityError
from django.test.utils import override_settings
from django.utils import timezone
from mock import patch

from bluebottle.members.models import MemberPlatformSettings, Member
from bluebottle.test.factory_models.accounts import BlueBottleUserFactory
from bluebottle.test.factory_models.geo import LocationFactory, CountryFactory
from bluebottle.test.utils import BluebottleTestCase


class BlueBottleUserManagerTestCase(BluebottleTestCase):
    """
    Test case for the model manager of the abstract user model.
    """

    def test_create_user(self):
        """
        Tests the manager ``create_user`` method.
        """

        user = BlueBottleUserFactory.create(
            email='john_doe@onepercentclub.com')

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_create_user_with_email(self):
        payload = {
            'email': 'john_doe@onepercentclub.com',
            'remote_id': 'john_doe@onepercentclub.com',
            'username': 'johny',
        }
        user = Member.objects.create_user(**payload)
        self.assertTrue(user.id)
        self.assertEqual(user.email, 'john_doe@onepercentclub.com')
        self.assertEqual(user.username, 'johny')

    def test_create_user_no_email_provided(self):
        """
        Tests exception raising when trying to create a new user without
        providing an email.
        """
        with self.assertRaises(IntegrityError):
            user = BlueBottleUserFactory.build()
            user.email = None
            user.save()

    def test_location_sets_country(self):
        country = CountryFactory.create()
        location = LocationFactory.create(country=country)
        BlueBottleUserFactory.create(email='john_doe@onepercentclub.com', location=location)


class BlueBottleUserTestCase(BluebottleTestCase):
    """
    Test case for the implementation of the abstract user model.
    """

    def setUp(self):
        self.init_projects()
        self.user = BlueBottleUserFactory.create()

    @patch('django.utils.timezone.now')
    def test_update_deleted_timestamp(self, mock):
        """
        Tests the ``update_deleted_timestamp`` method, checking that the
        timestamp is properly set up when the user is not active any more.
        """
        timestamp = timezone.now()
        mock.return_value = timestamp

        self.user.is_active = False
        self.user.update_deleted_timestamp()

        self.assertEqual(self.user.deleted, timestamp)

    def test_update_deleted_timestamp_active_user(self):
        """
        Tests that the ``update_deleted_timestamp`` method resets the timestamp
        to ``None`` if the user becomes active again.
        """
        self.user.is_active = False
        self.user.update_deleted_timestamp()

        # Now the user is inactive, so ``deleted`` attribute is set. Let's
        # reactivate it again and check that is reset.
        self.user.is_active = True
        self.user.update_deleted_timestamp()

        self.assertIsNone(self.user.deleted)

    def test_generate_username_from_email(self):
        """
        Tests the ``generate_username`` method when no username was provided.
        It should set the email as username.
        """
        user = BlueBottleUserFactory.create(email='piet@puk.nl', username='',
                                            first_name='', last_name='')
        user.generate_username()
        self.assertEqual(user.username, user.email)

    def test_get_full_name(self):
        """
        Tests the ``get_full_name`` method.
        """
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.save()

        self.assertEqual(self.user.get_full_name(), 'John Doe')

    def test_get_short_name(self):
        """
        Tests the ``get_short_name`` method.
        """
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.save()

        self.assertEqual(self.user.get_short_name(), 'John')

    @override_settings(SEND_WELCOME_MAIL=True,
                       CELERY_MAIL=False)
    def test_welcome_mail(self):
        """
        Test that a welcome mail is sent when a user is created when the
        setting are enabled
        """

        mail.outbox = []

        self.assertEqual(len(mail.outbox), 0)
        new_user = BlueBottleUserFactory.create(
            email='new_user@onepercentclub.com',
            primary_language='en')
        self.assertEqual(len(mail.outbox), 1)
        # We need a better way to verify the right mail is loaded
        self.assertTrue("Welcome" in mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].activated_language, 'en')
        self.assertEqual(mail.outbox[0].recipients()[0], new_user.email)
        self.assertTrue('[Set password](https://testserver/setpassword' in mail.outbox[0].body)

    @override_settings(SEND_WELCOME_MAIL=True,
                       CELERY_MAIL=False)
    def test_welcome_mail_password(self):
        """
        Test that a welcome mail is sent when a user is created when the
        setting are enabled
        """

        mail.outbox = []

        self.assertEqual(len(mail.outbox), 0)
        new_user = BlueBottleUserFactory.create(
            email='new_user@onepercentclub.com',
            password='test',
            primary_language='en')
        self.assertEqual(len(mail.outbox), 1)
        # We need a better way to verify the right mail is loaded
        self.assertTrue("Welcome" in mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].activated_language, 'en')
        self.assertEqual(mail.outbox[0].recipients()[0], new_user.email)
        self.assertTrue('[Take me there](https://testserver)' in mail.outbox[0].body)

    @override_settings(SEND_WELCOME_MAIL=True,
                       CELERY_MAIL=False)
    def test_welcome_mail_closed(self):
        """
        Test that a welcome mail is sent when a user is created when the
        setting are enabled
        """

        mail.outbox = []
        MemberPlatformSettings.objects.update(closed=True)

        self.assertEqual(len(mail.outbox), 0)
        new_user = BlueBottleUserFactory.create(
            email='new_user@onepercentclub.com',
            password='test',
            remote_id=None,
            primary_language='en')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual("Welcome to Test!", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].activated_language, 'en')
        self.assertEqual(mail.outbox[0].recipients()[0], new_user.email)
        self.assertTrue('[Take me there](https://testserver/partner)' in mail.outbox[0].body)

    @override_settings(SEND_WELCOME_MAIL=True,
                       CELERY_MAIL=False)
    def test_welcome_mail_closed_remote_id(self):
        """
        Test that a welcome mail is sent when a user is created when the
        setting are enabled
        """
        MemberPlatformSettings.objects.update(closed=True)
        mail.outbox = []

        self.assertEqual(len(mail.outbox), 0)
        new_user = BlueBottleUserFactory.create(
            email='new_user@onepercentclub.com',
            password='test',
            remote_id='123',
            primary_language='en')
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("Welcome" in mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].activated_language, 'en')
        self.assertEqual(mail.outbox[0].recipients()[0], new_user.email)
        self.assertTrue('[Take me there](https://testserver)' in mail.outbox[0].body)

    @override_settings(SEND_WELCOME_MAIL=True,
                       CELERY_MAIL=False)
    def test_welcome_mail_nl(self):
        """
        Test that a welcome mail is sent when a user is created when the
        setting are enabled (NL).
        """

        mail.outbox = []

        self.assertEqual(len(mail.outbox), 0)
        new_user = BlueBottleUserFactory.create(
            email='new_user@onepercentclub.com',
            primary_language='nl')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].activated_language, 'nl')
        self.assertEqual(mail.outbox[0].recipients()[0], new_user.email)

    def test_no_welcome_mail(self):
        """
        Test that a welcome mail is sent when a user is created when the setting
        are disabled (= default)
        """
        mail.outbox = []

        # The setup function also creates a user and generates a mail
        self.assertEqual(len(mail.outbox), 0)
        BlueBottleUserFactory.create(email='new_user@onepercentclub.com')
        self.assertEqual(len(mail.outbox), 0)

    def test_base_user_fields(self):
        """ Test that a base user model has all the expected fields """
        from bluebottle.members.models import Member

        user_fields = set(
            ['email', 'username', 'is_staff', 'is_active', 'date_joined',
             'updated', 'deleted',
             'user_type', 'first_name', 'last_name', 'location', 'picture',
             'about_me',
             'primary_language', 'share_time_knowledge', 'share_money',
             'newsletter', 'phone_number',
             'gender', 'birthdate', 'disable_token', 'campaign_notifications'])

        self.assertEqual(
            set(f.name for f in Member._meta.fields) & user_fields, user_fields)

    def test_anonymize(self):
        self.user.anonymize()

        for prop in [
            'is_active',
            'user_name',
            'place',
            'picture',
            'avatar',
            'about_me',
            'gender',
            'location',
            'website',
            'facebook',
            'twitter',
            'skypename',
            'partner_organization',
        ]:
            self.assertFalse(getattr(self.user, prop))

        self.assertEqual(self.user.birthdate, '1000-01-01')
        self.assertTrue(self.user.email.endswith('anonymous@example.com'))
        self.assertEqual(self.user.first_name, 'Deactivated')
        self.assertEqual(self.user.last_name, 'Member')
        self.assertEqual(self.user.is_anonymized, True)
        self.assertFalse(self.user.has_usable_password())

    def test_anonymize_twice(self):
        self.user.anonymize()

        other_user = BlueBottleUserFactory.create()
        other_user.anonymize()
        self.assertFalse(other_user.is_active)
