import functools
from builtins import object

from adminfilters.multiselect import UnionFieldListFilter
from adminsortable.admin import NonSortableParentAdmin
from django import forms
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.tokens import default_token_generator
from django.db import connection
from django.db import models
from django.db.models import Q
from django.forms import BaseInlineFormSet
from django.forms.widgets import Select
from django.http import HttpResponse
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.template import loader
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html
from django.utils.http import int_to_base36
from django.utils.translation import gettext_lazy as _
from django_admin_inline_paginator.admin import TabularInlinePaginated
from permissions_widget.forms import PermissionSelectMultipleField
from rest_framework.authtoken.models import Token

from bluebottle.bb_accounts.utils import send_welcome_mail
from bluebottle.bb_follow.models import Follow
from bluebottle.bluebottle_dashboard.decorators import confirmation_form
from bluebottle.clients import properties
from bluebottle.clients.utils import tenant_url
from bluebottle.collect.models import CollectContributor
from bluebottle.deeds.models import DeedParticipant
from bluebottle.funding.models import Donor, PaymentProvider
from bluebottle.funding_pledge.models import PledgePaymentProvider
from bluebottle.geo.models import Location
from bluebottle.initiatives.models import Initiative
from bluebottle.members.forms import (
    LoginAsConfirmationForm,
    SendWelcomeMailConfirmationForm,
    SendPasswordResetMailConfirmationForm
)
from bluebottle.members.models import (
    MemberPlatformSettings,
    UserActivity,
)
from bluebottle.notifications.models import Message
from bluebottle.segments.admin import SegmentAdminFormMetaClass
from bluebottle.segments.models import SegmentType
from bluebottle.time_based.models import DateParticipant, PeriodParticipant
from bluebottle.utils.admin import export_as_csv_action, BasePlatformSettingsAdmin
from bluebottle.utils.email_backend import send_mail
from bluebottle.utils.widgets import SecureAdminURLFieldWidget
from .models import Member, UserSegment


class MemberForm(forms.ModelForm, metaclass=SegmentAdminFormMetaClass):
    def __init__(self, data=None, files=None, current_user=None, *args, **kwargs):
        self.current_user = current_user
        super(MemberForm, self).__init__(data, files, *args, **kwargs)

        if self.current_user.is_superuser:
            # Super users can assign every group to a user
            group_queryset = Group.objects.all()
        else:
            # Normal staff users can only choose groups that they belong to.
            group_queryset = Group.objects.filter(
                pk__in=self.current_user.groups.all().only('pk')
            )

        self.fields['groups'] = forms.ModelMultipleChoiceField(
            queryset=group_queryset,
            required=False,
            initial=Group.objects.filter(name='Authenticated')
        )

    class Meta(object):
        model = Member
        # Mind you these fields are also set in MemberAdmin.add_fieldsets
        fields = '__all__'


class MemberCreationForm(MemberForm):
    """
    A form that creates a member.
    """
    error_messages = {
        'duplicate_email': _("A user with that email already exists."),
    }
    email = forms.EmailField(label=_("Email address"), max_length=254,
                             help_text=_("A valid, unique email address."))

    is_active = forms.BooleanField(label=_("Is active"), initial=True)

    def clean_email(self):
        # Since BlueBottleUser.email is unique, this check is redundant
        # but it sets a nicer error message than the ORM.
        email = self.cleaned_data["email"]
        try:
            Member._default_manager.get(email=email)
        except Member.DoesNotExist:
            return email
        raise forms.ValidationError(self.error_messages['duplicate_email'])

    def save(self, commit=True):
        user = super(MemberCreationForm, self).save(commit=False)
        if commit:
            user.save()
        return user


class MemberPlatformSettingsAdmin(BasePlatformSettingsAdmin, NonSortableParentAdmin):
    fieldsets = (
        (
            _('Login'),
            {
                'fields': (
                    'closed', 'confirm_signup', 'login_methods', 'email_domain',
                    'background',
                )
            }
        ),

        (
            _('Profile'),
            {
                'fields': (
                    'enable_gender', 'enable_birthdate', 'enable_segments',
                    'enable_address', 'create_segments'
                )
            }
        ),
        (
            _('Privacy'),
            {
                'fields': (
                    'session_only', 'require_consent', 'consent_link', 'anonymization_age'
                )
            }
        ),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = self.fieldsets
        required_fields = []
        if Location.objects.count():
            required_fields.append('require_office')
            required_fields.append('verify_office')
        if SegmentType.objects.count():
            required_fields.append('segment_types')

        if len(required_fields):
            fieldsets += ((
                _('Required fields'),
                {
                    'description': _('After logging in members are required to '
                                     'fill out or confirm the  fields listed below.'),
                    'fields': required_fields
                }
            ),)
        return fieldsets

    readonly_fields = ('segment_types',)

    def segment_types(self, obj):
        template = loader.get_template('segments/admin/required_segment_types.html')
        context = {
            'required': SegmentType.objects.filter(required=True).all(),
            'link': reverse('admin:segments_segmenttype_changelist')
        }
        return template.render(context)


admin.site.register(MemberPlatformSettings, MemberPlatformSettingsAdmin)


class SegmentSelect(Select):
    template_name = 'widgets/segment-select.html'

    def __init__(self, verified):
        self.verified = verified
        super().__init__()

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['verified'] = self.verified
        return context


class MemberChangeForm(MemberForm):
    """
    Change Member form
    """

    email = forms.EmailField(label=_("email address"), max_length=254,
                             help_text=_("A valid, unique email address."))

    class Meta(object):
        model = Member
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(MemberChangeForm, self).__init__(*args, **kwargs)
        f = self.fields.get('user_permissions', None)
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')

        if connection.tenant.schema_name != 'public':
            for segment_type in SegmentType.objects.all():
                user_segment = UserSegment.objects.filter(
                    member=self.instance, segment__segment_type=segment_type
                ).first()

                self.fields[segment_type.field_name] = forms.ModelChoiceField(
                    required=False,
                    label=segment_type.name,
                    queryset=segment_type.segments,
                    widget=SegmentSelect(verified=user_segment.verified if user_segment else None)
                )
                self.initial[segment_type.field_name] = user_segment.segment if user_segment else None

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]

    def save(self, commit=True):
        member = super(MemberChangeForm, self).save(commit=commit)
        segments = []
        for segment_type in SegmentType.objects.all():
            segment = self.cleaned_data.get(segment_type.field_name, None)
            if segment:
                segments.append(segment)
        member.segments.set(segments)
        return member


class LimitModelFormset(BaseInlineFormSet):
    """ Base Inline formset to limit inline Model query results. """
    LIMIT = 20

    def __init__(self, *args, **kwargs):
        super(LimitModelFormset, self).__init__(*args, **kwargs)
        _kwargs = {self.fk.name: kwargs['instance']}
        self.queryset = kwargs['queryset'].filter(**_kwargs).order_by('-id')[:self.LIMIT]


class UserActivityInline(admin.TabularInline):

    readonly_fields = ['created', 'user', 'path']
    extra = 0
    model = UserActivity
    can_delete = False

    formset = LimitModelFormset

    def has_add_permission(self, request, obj=None):
        return False


class SortedUnionFieldListFilter(UnionFieldListFilter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lookup_choices = sorted(self.lookup_choices, key=lambda a: a[1].lower())


class MemberMessagesInline(TabularInlinePaginated):
    model = Message
    per_page = 20
    ordering = ('-sent',)
    readonly_fields = [
        'sent', 'template', 'subject', 'content_type', 'related'
    ]
    fields = readonly_fields

    def related(self, obj):
        url = f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change"
        if not obj.content_object:
            return format_html('{}<br><i>{}</i>', obj.content_type, _('Deleted'))
        try:
            return format_html(
                u"<a href='{}'>{}</a>",
                str(reverse(url, args=(obj.object_id,))), obj.content_object or obj.content_type or 'Related object'
            )
        except NoReverseMatch:
            return obj.content_object or 'Related object'


class MemberAdmin(UserAdmin):
    raw_id_fields = ('partner_organization', 'place')
    date_hierarchy = 'date_joined'

    formfield_overrides = {
        models.URLField: {'widget': SecureAdminURLFieldWidget()},
    }

    def get_form(self, request, *args, **kwargs):
        Form = super(MemberAdmin, self).get_form(request, *args, **kwargs)
        return functools.partial(Form, current_user=request.user)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            fieldsets = ((
                None, {
                    'classes': ('wide', ),
                    'fields': [
                        'first_name', 'last_name', 'email', 'is_active',
                        'is_staff', 'groups'
                    ]
                }
            ), )
        else:
            fieldsets = [
                [
                    _("Main"),
                    {
                        'fields': [
                            'email',
                            'remote_id',
                            'first_name',
                            'last_name',
                            'phone_number',
                            'login_as_link',
                            'reset_password',
                            'resend_welcome_link',
                            'last_login',
                            'date_joined',
                            'deleted',
                            'partner_organization',
                            'primary_language',
                        ]
                    }
                ],
                [
                    _("Profile"),
                    {
                        'fields':
                        ['picture', 'about_me', 'matching_options_set',
                         'favourite_themes', 'skills', 'place']

                    }
                ],
                [
                    _('Permissions'),
                    {'fields': [
                        'is_active',
                        'is_staff',
                        'is_superuser',
                        'groups',
                        'is_co_financer',
                        'can_pledge',
                        'verified',
                        'kyc'
                    ]}
                ],
                [
                    _('Engagement'),
                    {
                        'fields':
                        [
                            'initiatives',
                            'date_activities',
                            'period_activities',
                            'funding',
                            'deeds',
                            'collect',
                        ]
                    }
                ],
                [
                    _('Notifications'),
                    {
                        'fields':
                        ['campaign_notifications', 'subscribed']
                    }
                ],
            ]

            if Location.objects.count():
                fieldsets[1][1]['fields'].append('location')

            member_settings = MemberPlatformSettings.load()

            if member_settings.enable_gender:
                fieldsets[0][1]['fields'].append('gender')
            if member_settings.enable_birthdate:
                fieldsets[0][1]['fields'].append('birthdate')

            if not PaymentProvider.objects.filter(Q(instance_of=PledgePaymentProvider)).count():
                fieldsets[2][1]['fields'].remove('can_pledge')

            if obj and (obj.is_staff or obj.is_superuser):
                fieldsets[4][1]['fields'].append('submitted_initiative_notifications')

            if SegmentType.objects.count():
                extra = (
                    _('Segments'), {
                        'fields': [
                            segment_type.field_name
                            for segment_type in SegmentType.objects.all()
                        ]
                    }
                )

                fieldsets.insert(2, extra)

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = [
            'date_joined', 'last_login',
            'updated', 'deleted', 'login_as_link',
            'reset_password', 'resend_welcome_link',
            'initiatives', 'period_activities', 'date_activities',
            'funding', 'deeds', 'collect', 'kyc'
        ]

        user_groups = request.user.groups.all()

        if obj and hasattr(obj, 'groups') and not request.user.is_superuser:
            for group in obj.groups.all():
                if group not in user_groups:
                    readonly_fields.append('email')

        if not request.user.is_superuser:
            if obj and obj.is_superuser:
                readonly_fields.append('email')

            readonly_fields.append('is_superuser')

        return readonly_fields

    export_fields = (
        ('email', 'email'),
        ('phone_number', 'phone number'),
        ('remote_id', 'remote id'),
        ('first_name', 'first name'),
        ('last_name', 'last name'),
        ('date_joined', 'date joined'),

        ('is_initiator', 'is initiator'),
        ('is_supporter', 'is supporter'),
        ('is_volunteer', 'is volunteer'),
        ('amount_donated', 'amount donated'),
        ('time_spent', 'time spent'),
        ('subscribed', 'subscribed to matching projects'),
    )

    def get_export_fields(self):
        fields = self.export_fields
        member_settings = MemberPlatformSettings.load()
        if member_settings.enable_gender:
            fields += (('gender', 'gender'),)
        if member_settings.enable_birthdate:
            fields += (('birthdate', 'birthdate'),)
        if member_settings.enable_address:
            fields += (('place__street', 'street'),)
            fields += (('place__street_number', 'street_number'),)
            fields += (('place__locality', 'city'),)
            fields += (('place__postal_code', 'postal_code'),)
            fields += (('place__country__name', 'country'),)
        return fields

    def get_actions(self, request):
        self.actions = (export_as_csv_action(fields=self.get_export_fields()),)

        return super(MemberAdmin, self).get_actions(request)

    form = MemberChangeForm
    add_form = MemberCreationForm

    list_filter = (
        'is_active',
        'newsletter',
        ('favourite_themes', SortedUnionFieldListFilter),
        ('skills', SortedUnionFieldListFilter),
        ('groups', UnionFieldListFilter)
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff',
                    'date_joined', 'is_active', 'login_as_link')
    ordering = ('-date_joined', 'email',)

    inlines = (UserActivityInline, MemberMessagesInline)

    def initiatives(self, obj):
        initiatives = []
        initiative_url = reverse('admin:initiatives_initiative_changelist')
        for field in ['owner', 'reviewer', 'promoter', 'activity_managers']:
            if Initiative.objects.filter(status__in=['draft', 'submitted', 'needs_work'], **{field: obj}).count():
                link = initiative_url + '?{}_id={}'.format(field, obj.id)
                initiatives.append(format_html(
                    '<a href="{}">{}</a> draft {}',
                    link,
                    Initiative.objects.filter(status__in=['draft', 'submitted', 'needs_work'], **{field: obj}).count(),
                    field,
                ))
            if Initiative.objects.filter(status='approved', **{field: obj}).count():
                link = initiative_url + '?{}_id={}'.format(field, obj.id)
                initiatives.append(format_html(
                    '<a href="{}">{}</a> open {}',
                    link,
                    Initiative.objects.filter(status='approved', **{field: obj}).count(),
                    field,
                ))
        return format_html('<br/>'.join(initiatives)) or _('None')
    initiatives.short_description = _('Initiatives')

    def date_activities(self, obj):
        participants = []
        participant_url = reverse('admin:time_based_dateparticipant_changelist')
        for status in ['new', 'accepted', 'withdrawn', 'rejected']:
            if DateParticipant.objects.filter(status=status, user=obj).count():
                link = participant_url + '?user_id={}&status={}'.format(obj.id, status)
                participants.append(format_html(
                    '<a href="{}">{}</a> {}',
                    link,
                    DateParticipant.objects.filter(status=status, user=obj).count(),
                    status,
                ))
        return format_html('<br/>'.join(participants)) or _('None')
    date_activities.short_description = _('Activity on a date participation')

    def period_activities(self, obj):
        applicants = []
        applicant_url = reverse('admin:time_based_periodparticipant_changelist')
        for status in ['new', 'accepted', 'withdrawn', 'rejected']:
            if PeriodParticipant.objects.filter(status=status, user=obj).count():
                link = applicant_url + '?user_id={}&status={}'.format(obj.id, status)
                applicants.append(format_html(
                    '<a href="{}">{}</a> {}',
                    link,
                    PeriodParticipant.objects.filter(status=status, user=obj).count(),
                    status,
                ))
        return format_html('<br/>'.join(applicants)) or _('None')
    date_activities.short_description = _('Activity during a date participation')

    def funding(self, obj):
        donations = []
        donation_url = reverse('admin:funding_donor_changelist')
        if Donor.objects.filter(status='succeeded', user=obj).count():
            link = donation_url + '?user_id={}'.format(obj.id)
            donations.append(format_html(
                '<a href="{}">{}</a> donations',
                link,
                Donor.objects.filter(status='succeeded', user=obj).count(),
            ))
        return format_html('<br/>'.join(donations)) or _('None')
    funding.short_description = _('Funding donations')

    def deeds(self, obj):
        participants = []
        participant_url = reverse('admin:deeds_deedparticipant_changelist')
        for status in ['new', 'accepted', 'withdrawn', 'rejected', 'succeeded']:
            if DeedParticipant.objects.filter(status=status, user=obj).count():
                link = participant_url + '?user_id={}&status={}'.format(obj.id, status)
                participants.append(format_html(
                    '<a href="{}">{}</a> {}',
                    link,
                    DeedParticipant.objects.filter(status=status, user=obj).count(),
                    status,
                ))
        return format_html('<br/>'.join(participants)) or _('None')
    deeds.short_description = _('Deed participation')

    def collect(self, obj):
        participants = []
        participant_url = reverse('admin:collect_collectcontributor_changelist')
        for status in ['new', 'accepted', 'withdrawn', 'rejected', 'succeeded']:
            if CollectContributor.objects.filter(status=status, user=obj).count():
                link = participant_url + '?user_id={}&status={}'.format(obj.id, status)
                participants.append(format_html(
                    '<a href="{}">{}</a> {}',
                    link,
                    CollectContributor.objects.filter(status=status, user=obj).count(),
                    status,
                ))
        return format_html('<br/>'.join(participants)) or _('None')
    collect.short_description = _('Collect contributor')

    def following(self, obj):
        url = reverse('admin:bb_follow_follow_changelist')
        follow_count = Follow.objects.filter(user=obj).count()
        return format_html('<a href="{}?user_id={}">{} objects</a>', url, obj.id, follow_count)
    following.short_description = _('Following')

    def reset_password(self, obj):
        reset_mail_url = reverse('admin:auth_user_password_reset_mail', kwargs={'pk': obj.id})
        properties.set_tenant(connection.tenant)

        return format_html(
            "<a href='{}'>{}</a>",
            reset_mail_url, _("Send reset password mail")
        )

    def resend_welcome_link(self, obj):
        welcome_mail_url = reverse('admin:auth_user_resend_welcome_mail', kwargs={'pk': obj.id})
        return format_html(
            "<a href='{}'>{}</a>",
            welcome_mail_url, _("Resend welcome email"),
        )

    def kyc(self, obj):
        if not obj.funding_payout_account.count():
            return '-'
        kyc_url = reverse('admin:funding_payoutaccount_changelist') + '?owner__id__exact={}'.format(obj.id)
        return format_html(
            "<a href='{}'>{} {}</a>",
            kyc_url,
            obj.funding_payout_account.count(),
            _("accounts")
        )
    kyc.short_description = _("KYC accounts")

    def get_inline_instances(self, request, obj=None):
        """ Override get_inline_instances so that the add form does not show inlines """
        if not obj:
            return []
        return super(MemberAdmin, self).get_inline_instances(request, obj)

    def get_urls(self):
        urls = super(MemberAdmin, self).get_urls()

        extra_urls = [
            url(r'^login-as/(?P<pk>\d+)/$',
                self.admin_site.admin_view(self.login_as),
                name='members_member_login_as'
                ),
            url(r'^password-reset/(?P<pk>\d+)/$',
                self.send_password_reset_mail,
                name='auth_user_password_reset_mail'
                ),
            url(r'^resend_welcome_email/(?P<pk>\d+)/$',
                self.resend_welcome_email,
                name='auth_user_resend_welcome_mail'
                )
        ]
        return extra_urls + urls

    @confirmation_form(
        SendPasswordResetMailConfirmationForm,
        Member,
        'admin/members/password_reset.html'
    )
    def send_password_reset_mail(self, request, user):
        if not request.user.has_perm('members.change_member'):
            return HttpResponseForbidden('Not allowed to change user')

        context = {
            'email': user.email,
            'site': tenant_url(),
            'site_name': tenant_url(),
            'uid': int_to_base36(user.pk),
            'user': user,
            'token': default_token_generator.make_token(user),
        }
        subject = loader.render_to_string('bb_accounts/password_reset_subject.txt', context)
        subject = ''.join(subject.splitlines())
        send_mail(
            template_name='bb_accounts/password_reset_email',
            to=user,
            subject=subject,
            **context
        )
        message = _('User {name} will receive an email to reset password.').format(name=user.full_name)
        self.message_user(request, message)
        return HttpResponseRedirect(reverse('admin:members_member_change', args=(user.id, )))

    @confirmation_form(
        SendWelcomeMailConfirmationForm,
        Member,
        'admin/members/resend_welcome_mail.html'
    )
    def resend_welcome_email(self, request, user):
        if not request.user.has_perm('members.change_member'):
            return HttpResponseForbidden('Not allowed to change user')

        send_welcome_mail(user)

        message = _('User {name} will receive an welcome email.').format(name=user.full_name)
        self.message_user(request, message)

        return HttpResponseRedirect(reverse('admin:members_member_change', args=(user.id, )))

    @confirmation_form(
        LoginAsConfirmationForm,
        Member,
        'admin/members/login_as.html'
    )
    def login_as(self, request, user):
        template = loader.get_template('utils/login_with.html')
        context = {'token': user.get_jwt_token(), 'link': '/'}
        response = HttpResponse(template.render(context, request), content_type='text/html')
        response['cache-control'] = "no-store, no-cache, private"
        return response

    def login_as_link(self, obj):
        url = reverse('admin:members_member_login_as', args=(obj.pk,))
        return format_html(
            u"<a target='_blank' href='{}'>{}</a>",
            url, _('Login as user')
        )
    login_as_link.short_description = _('Login as')

    def has_delete_permission(self, request, obj=None):
        if obj and obj.contributor_set.exclude(status__in=['deleted', 'failed']).count() == 0:
            return True
        return False


admin.site.register(Member, MemberAdmin)


class NewGroupChangeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Dynamically set permission widget to make it Tenant aware
        super(NewGroupChangeForm, self).__init__(*args, **kwargs)
        permissions = Permission.objects.all()
        self.fields['permissions'] = PermissionSelectMultipleField(queryset=permissions, required=False)


class GroupsAdmin(GroupAdmin):
    list_display = ["name", ]
    form = NewGroupChangeForm

    class Media(object):
        css = {
            'all': ('css/admin/permissions-table.css',)
        }

    class Meta(object):
        model = Group


admin.site.unregister(Group)
admin.site.register(Group, GroupsAdmin)


class TokenAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    readonly_fields = ('key',)
    fields = ('user', 'key')


admin.site.register(Token, TokenAdmin)
