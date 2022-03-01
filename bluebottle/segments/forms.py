from django import forms
from django.utils.translation import gettext_lazy as _


class SegmentTypeRequiredConfirmationForm(forms.Form):
    title = _('Segment type is required')


class SegmentTypeNeedsVerificatiConfirmationForm(forms.Form):
    title = _('Segment type needs verification')
