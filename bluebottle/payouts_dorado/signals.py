from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from bluebottle.projects.models import Project

from .adapters import DoradoPayoutAdapter


@receiver(post_save, weak=False, sender=Project,
          dispatch_uid='project_payout_create')
def trigger_payout_on_project_end(sender, instance, **kwargs):
    project = instance
    if project.status.slug in ['done-complete', 'done-incomplete'] \
            and project.amount_asked.amount:
        adapter = DoradoPayoutAdapter(project)
        adapter.trigger_payout()
