from tenant_extras.utils import TenantLanguage

from bluebottle.clients import properties
from bluebottle.notifications.models import Message


class TransitionMessage(object):
    """
    Base model for sending message
    When the subject contains a variable it should be specified in context, e.g.
    subject = "Un update on {initiative_title}"
    context = {'initiative_title': 'title'}
    The value is taken as an attribute of the related object (self.obj).
    So in the example if the transition is on initiative it wil be `initiative.title`.
    """
    subject = 'Status changed'
    template = 'messages/base'
    context = {}

    def __init__(self, obj):
        self.obj = obj

    def __unicode__(self):
        return self.subject

    def get_template(self):
        return self.template

    def get_subject(self, language=None):
        if not language:
            language = properties.LANGUAGE_CODE
        with TenantLanguage(language):
            context = {}
            for key, item in self.context.items():
                context[key] = getattr(self.obj, item)
            return self.subject.format(**context)

    def get_messages(self):
        return [
            Message(
                template=self.get_template(),
                subject=self.get_subject(recipient.primary_language),
                content_object=self.obj,
                recipient=recipient
            ) for recipient in self.get_recipients()
        ]

    def get_recipients(self):
        return [self.obj.owner]

    def compose_and_send(self, custom_message=None):
        for message in self.get_messages():
            message.custom_message = custom_message
            message.save()
            message.send()
