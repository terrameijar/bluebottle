from bluebottle.tasks.serializers import TaskPreviewSerializer
from django.db import connection
from django.db.models import Sum

from memoize import memoize

from bluebottle.bluebottle_drf2.serializers import ImageSerializer, SorlImageField
from bluebottle.members.models import Member
from bluebottle.members.serializers import UserPreviewSerializer
from bluebottle.orders.models import Order
from bluebottle.projects.models import Project
from bluebottle.statistics.statistics import Statistics

from rest_framework import serializers

from bluebottle.cms.models import (
    Stat, StatsContent, ResultPage, QuotesContent, SurveyContent, Quote,
    ProjectImagesContent, ProjectsContent, ShareResultsContent, ProjectsMapContent,
    SupporterTotalContent, TasksContent)
from bluebottle.projects.serializers import ProjectPreviewSerializer, ProjectTinyPreviewSerializer
from bluebottle.surveys.serializers import QuestionSerializer


class RichTextContentSerializer(serializers.Serializer):
    text = serializers.CharField()

    class Meta:
        fields = ('text', 'type')


class MediaFileContentSerializer(serializers.Serializer):
    url = serializers.CharField(source='mediafile.file.url')
    caption = serializers.CharField(source='mediafile.translation.caption')

    def get_url(self, obj):
        return obj.file.url

    class Meta:
        fields = ('url', 'type')


class StatSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    def get_value(self, obj):
        if obj.value:
            return obj.value

        statistics = Statistics(
            start=self.context['start_date'],
            end=self.context['end_date'],
        )

        value = getattr(statistics, obj.type, 0)
        try:
            return {
                'amount': value.amount,
                'currency': str(value.currency)
            }
        except AttributeError:
            return value

    class Meta:
        model = Stat
        fields = ('id', 'title', 'type', 'value')


class StatsContentSerializer(serializers.ModelSerializer):
    stats = StatSerializer(source='stats', many=True)
    title = serializers.CharField()
    sub_title = serializers.CharField()

    class Meta:
        model = QuotesContent
        fields = ('id', 'type', 'stats', 'title', 'sub_title')


class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ('id', 'name', 'quote')


class QuotesContentSerializer(serializers.ModelSerializer):
    quotes = QuoteSerializer(source='quotes', many=True)

    class Meta:
        model = QuotesContent
        fields = ('id', 'quotes', 'type', 'title', 'sub_title')


class SurveyContentSerializer(serializers.ModelSerializer):
    answers = QuestionSerializer(many=True, source='survey.visible_questions')
    response_count = serializers.SerializerMethodField()

    def get_response_count(self, obj):
        return obj.survey.response_set.count()

    class Meta:
        model = SurveyContent
        fields = ('id', 'type', 'response_count', 'answers', 'title', 'sub_title')


class ProjectImageSerializer(serializers.ModelSerializer):
    photo = ImageSerializer(source='image')

    class Meta:
        model = Project
        fields = ('id', 'photo', 'title', 'slug')


class ProjectImagesContentSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    def get_images(self, obj):
        projects = Project.objects.filter(
            campaign_ended__gte=self.context['start_date'],
            campaign_ended__lte=self.context['end_date'],
            status__slug__in=['done-complete', 'done-incomplete']).order_by('?')[:8]

        return ProjectImageSerializer(projects, many=True).to_representation(projects)

    class Meta:
        model = ProjectImagesContent
        fields = ('id', 'type', 'images', 'title', 'sub_title', 'description',
                  'action_text', 'action_link')


class ProjectsMapContentSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    @memoize(timeout=60 * 60)
    def get_projects(self, obj):
        projects = Project.objects.filter(
            campaign_ended__gte=self.context['start_date'],
            campaign_ended__lte=self.context['end_date'],
            status__slug__in=['done-complete', 'done-incomplete']
        ).order_by(
            '-status__sequence',
            'campaign_ended'
        )

        return ProjectTinyPreviewSerializer(projects, many=True).to_representation(projects)

    def __repr__(self):
        start = self.context['start_date'].strftime('%s') if self.context['start_date'] else 'none'
        end = self.context['end_date'].strftime('%s') if self.context['end_date'] else 'none'
        return 'MapsContent({},{})'.format(start, end)

    class Meta:
        model = ProjectImagesContent
        fields = ('id', 'type', 'title', 'sub_title', 'projects',)


class ProjectsContentSerializer(serializers.ModelSerializer):
    projects = ProjectPreviewSerializer(many=True, source='projects.projects')

    class Meta:
        model = ProjectsContent
        fields = ('id', 'type', 'title', 'sub_title', 'projects',
                  'action_text', 'action_link')


class TasksContentSerializer(serializers.ModelSerializer):
    tasks = TaskPreviewSerializer(many=True)

    class Meta:
        model = TasksContent
        fields = ('id', 'type', 'title', 'sub_title', 'tasks',
                  'action_text', 'action_link')


class ShareResultsContentSerializer(serializers.ModelSerializer):
    statistics = serializers.SerializerMethodField()

    def get_statistics(self, instance):
        stats = Statistics(
            start=self.context['start_date'],
            end=self.context['end_date']
        )

        return {
            'people': stats.people_involved,
            'amount': {
                'amount': stats.donated_total.amount,
                'currency': str(stats.donated_total.currency)
            },
            'hours': stats.time_spent,
            'projects': stats.projects_realized,
            'tasks': stats.tasks_realized,
            'votes': stats.votes_cast,
        }

    class Meta:
        model = ShareResultsContent
        fields = ('id', 'type', 'title', 'sub_title',
                  'statistics', 'share_title', 'share_text')


class CoFinancerSerializer(serializers.Serializer):
    total = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    def get_user(self, obj):
        user = Member.objects.get(pk=obj['user'])
        return UserPreviewSerializer(
            user, context=self.context
        ).to_representation(user)

    def get_id(self, obj):
        return obj['user']

    def get_total(self, obj):
        return {
            'amount': obj['total'],
            'currency': obj['total_currency']
        }

    class Meta:
        fields = ('id', 'user', 'total')


class SupporterTotalContentSerializer(serializers.ModelSerializer):
    supporters = serializers.SerializerMethodField()
    co_financers = serializers.SerializerMethodField()

    def get_supporters(self, instance):
        stats = Statistics(
            start=self.context['start_date'],
            end=self.context['end_date']
        )
        return stats.people_involved

    def get_co_financers(self, instance):
        totals = Order.objects. \
            filter(confirmed__gte=self.context['start_date']). \
            filter(confirmed__lte=self.context['end_date']). \
            filter(status__in=['pending', 'success']). \
            filter(user__is_co_financer=True). \
            values('user', 'total_currency'). \
            annotate(total=Sum('total'))
        return CoFinancerSerializer(
            totals, many=True, context=self.context
        ).to_representation(totals)

    class Meta:
        model = SupporterTotalContent
        fields = ('id', 'type',
                  'title', 'sub_title', 'co_financer_title',
                  'supporters', 'co_financers')


class BlockSerializer(serializers.Serializer):
    def to_representation(self, obj):
        if isinstance(obj, StatsContent):
            serializer = StatsContentSerializer
        if isinstance(obj, QuotesContent):
            serializer = QuotesContentSerializer
        if isinstance(obj, ProjectImagesContent):
            serializer = ProjectImagesContentSerializer
        if isinstance(obj, SurveyContent):
            serializer = SurveyContentSerializer
        if isinstance(obj, ProjectsContent):
            serializer = ProjectsContentSerializer
        if isinstance(obj, ShareResultsContent):
            serializer = ShareResultsContentSerializer
        if isinstance(obj, ProjectsMapContent):
            serializer = ProjectsMapContentSerializer
        if isinstance(obj, SupporterTotalContent):
            serializer = SupporterTotalContentSerializer
        if isinstance(obj, TasksContent):
            serializer = TasksContentSerializer

        return serializer(obj, context=self.context).to_representation(obj)


def watermark():
    return '{}/logo-overlay.png'.format(connection.tenant.client_name)


class ResultPageSerializer(serializers.ModelSerializer):
    blocks = BlockSerializer(source='content.contentitems.all.translated', many=True)
    image = ImageSerializer()
    share_image = SorlImageField(
        '1200x600', source='image', crop='center',
        watermark=watermark,
        watermark_pos='center', watermark_size='1200x600'
    )

    class Meta:
        model = ResultPage
        fields = ('id', 'title', 'slug', 'start_date', 'image', 'share_image',
                  'end_date', 'description', 'blocks')
