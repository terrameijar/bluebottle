from bluebottle.bluebottle_drf2.serializers import ImageSerializer
from bluebottle.projects.models import Project
from bluebottle.statistics.statistics import Statistics
from rest_framework import serializers

from bluebottle.cms.models import (
    Stat, StatsContent, ResultPage, QuotesContent, SurveyContent, Quote,
    ProjectImagesContent, ProjectsContent, ShareResultsContent, ProjectsMapContent
)
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
            start=self.context['start_date'].strftime('%Y-%m-%d 00:00+00:00'),
            end=self.context['end_date'].strftime('%Y-%m-%d 00:00+00:00'),
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
    stats = StatSerializer(source='stats.stat_set', many=True)
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
    quotes = QuoteSerializer(source='quotes.quote_set', many=True)

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
            campaign_ended__gte=self.context['start_date'].strftime('%Y-%m-%d 00:00+00:00'),
            campaign_ended__lte=self.context['end_date'].strftime('%Y-%m-%d 00:00+00:00'),
            status__slug__in=['done-complete', 'done-incomplete']).order_by('?')

        return ProjectImageSerializer(projects, many=True).to_representation(projects)

    class Meta:
        model = ProjectImagesContent
        fields = ('id', 'type', 'images', 'title', 'sub_title', 'description',
                  'action_text', 'action_link')


class ProjectsMapContentSerializer(serializers.ModelSerializer):
    projects = serializers.SerializerMethodField()

    def get_projects(self, obj):
        projects = Project.objects.filter(
            campaign_ended__gte=self.context['start_date'].strftime('%Y-%m-%d 00:00+00:00'),
            campaign_ended__lte=self.context['end_date'].strftime('%Y-%m-%d 00:00+00:00'),
            status__slug__in=['done-complete', 'done-incomplete'])

        return ProjectTinyPreviewSerializer(projects, many=True).to_representation(projects)

    class Meta:
        model = ProjectImagesContent
        fields = ('id', 'type', 'title', 'sub_title', 'projects', )


class ProjectsContentSerializer(serializers.ModelSerializer):
    projects = ProjectPreviewSerializer(many=True, source='projects.projects')

    class Meta:
        model = ProjectsContent
        fields = ('id', 'type', 'title', 'sub_title', 'projects',
                  'action_text', 'action_link')


class ShareResultsContentSerializer(serializers.ModelSerializer):
    statistics = serializers.SerializerMethodField()

    def get_statistics(self, instance):
        stats = Statistics(
            start=self.context['start_date'].strftime('%Y-%m-%d 00:00+00:00'),
            end=self.context['end_date'].strftime('%Y-%m-%d 00:00+00:00')
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
        fields = ('id', 'type', 'title', 'sub_title', 'statistics', 'share_text')


class BlockSerializer(serializers.Serializer):

    def to_representation(self, obj):
        if isinstance(obj, StatsContent):
            return StatsContentSerializer(obj, context=self.context).to_representation(obj)
        if isinstance(obj, QuotesContent):
            return QuotesContentSerializer(obj, context=self.context).to_representation(obj)
        if isinstance(obj, ProjectImagesContent):
            return ProjectImagesContentSerializer(obj, context=self.context).to_representation(obj)
        if isinstance(obj, SurveyContent):
            return SurveyContentSerializer(obj, context=self.context).to_representation(obj)
        if isinstance(obj, ProjectsContent):
            return ProjectsContentSerializer(obj, context=self.context).to_representation(obj)
        if isinstance(obj, ShareResultsContent):
            return ShareResultsContentSerializer(obj, context=self.context).to_representation(obj)
        if isinstance(obj, ProjectsMapContent):
            return ProjectsMapContentSerializer(obj, context=self.context).to_representation(obj)


class ResultPageSerializer(serializers.ModelSerializer):
    blocks = BlockSerializer(source='content.contentitems.all.translated', many=True)
    image = ImageSerializer()

    class Meta:
        model = ResultPage
        fields = ('id', 'title', 'slug', 'start_date', 'image',
                  'end_date', 'description', 'blocks')
