import datetime

from django.contrib.auth.models import User, Group, Permission
from django.core import mail
from django.test.client import RequestFactory
from django.utils import timezone

from nose.tools import ok_
from funfactory.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.suggest import sending
from airmozilla.main.models import (
    Event,
    SuggestedEvent,
    SuggestedEventComment,
    Location,
)


class TestSending(DjangoTestCase):
    placeholder = 'airmozilla/manage/tests/firefox.png'

    def test_email_about_suggested_event_comment(self):
        # first we need to add two users
        zandr = User.objects.create(
            username='zandr',
            email='zandr@mozilla.com'
        )
        permission = Permission.objects.get(codename='add_event')
        group = Group.objects.create(name='testapprover')
        group.permissions.add(permission)
        zandr.groups.add(group)

        richard = User.objects.create(
            username='richard',
            email='richard@mozilla.com',
            is_staff=True,
            is_superuser=True
        )

        user, = User.objects.all()[:1]
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)

        suggested_event = SuggestedEvent.objects.create(
            user=user,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            first_submitted=now,
            submitted=now
        )
        comment = SuggestedEventComment.objects.create(
            comment="Bla bla",
            user=user,
            suggested_event=suggested_event
        )
        request = RequestFactory().get('/')
        # bob = User.objects.create(email='bob@mozilla.com')
        sending.email_about_suggested_event_comment(comment, request)
        email_sent = mail.outbox[-1]
        ok_(email_sent.alternatives)
        ok_(richard.email in email_sent.recipients())
        ok_(zandr.email in email_sent.recipients())
        ok_('TITLE' in email_sent.subject)
        summary_url = reverse('suggest:summary', args=(suggested_event.pk,))
        ok_(summary_url in email_sent.body)

    def test_email_about_suggested_event(self):
        # first we need to add two users
        zandr = User.objects.create(
            username='zandr',
            email='zandr@mozilla.com'
        )
        permission = Permission.objects.get(codename='add_event')
        group = Group.objects.create(name='testapprover')
        group.permissions.add(permission)
        zandr.groups.add(group)

        richard = User.objects.create(
            username='richard',
            email='richard@mozilla.com',
            is_staff=True,
            is_superuser=True
        )

        user, = User.objects.all()[:1]
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)

        suggested_event = SuggestedEvent.objects.create(
            user=user,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            first_submitted=now,
            submitted=now
        )

        request = RequestFactory().get('/')
        # bob = User.objects.create(email='bob@mozilla.com')
        sending.email_about_suggested_event(suggested_event, request)
        email_sent = mail.outbox[-1]
        ok_(email_sent.alternatives)
        ok_(richard.email in email_sent.recipients())
        ok_(zandr.email in email_sent.recipients())
        ok_('TITLE' in email_sent.subject)
        ok_('TITLE' in email_sent.body)
        summary_url = reverse('suggest:summary', args=(suggested_event.pk,))
        ok_(summary_url in email_sent.body)
