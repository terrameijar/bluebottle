import dateutil

from elasticsearch_dsl.query import FunctionScore, SF, Terms, Term, Nested, Q, Range
from bluebottle.utils.filters import ElasticSearchFilter
from bluebottle.activities.documents import activity


class ActivitySearchFilter(ElasticSearchFilter):
    document = activity

    sort_fields = {
        'date': ('-created', ),
        'alphabetical': ('title_keyword', ),
        'popularity': 'popularity',
    }

    filters = (
        'owner.id',
        'theme.id',
        'country',
        'categories.slug',
        'expertise.id',
        'type',
        'status',
        'date',
    )

    search_fields = (
        'status', 'title', 'description', 'owner.full_name',
    )

    boost = {'title': 2}

    def get_sort_popularity(self, request):
        score = FunctionScore(
            score_mode='sum',
            functions=[
                SF(
                    'field_value_factor',
                    field='status_score',
                    factor=1
                ),
                SF(
                    'gauss',
                    weight=0.001,
                    created={
                        'scale': "365d"
                    },
                ),
            ]
        ) | FunctionScore(
            score_mode='multiply',
            functions=[
                SF(
                    'field_value_factor',
                    field='contribution_count',
                    missing=0
                ),
                SF(
                    'gauss',
                    weight=0.1,
                    multi_value_mode='avg',
                    contributions={
                        'scale': '5d'
                    },
                ),
            ]
        )

        if request.user.is_authenticated:
            if request.user.skills:
                score = score | FunctionScore(
                    score_mode='first',
                    functions=[
                        SF({
                            'filter': Nested(
                                path='expertise',
                                query=Q(
                                    'terms',
                                    expertise__id=[skill.pk for skill in request.user.skills.all()]
                                )
                            ),
                            'weight': 0.1,
                        }),
                        SF({'weight': 0}),
                    ]
                )

            if request.user.favourite_themes:
                score = score | FunctionScore(
                    score_mode='first',
                    functions=[
                        SF({
                            'filter': Nested(
                                path='theme',
                                query=Q(
                                    'terms',
                                    theme__id=[theme.pk for theme in request.user.favourite_themes.all()]
                                )
                            ),
                            'weight': 0.1,
                        }),
                        SF({'weight': 0}),
                    ]
                )

            position = None
            if request.user.location and request.user.location.position:
                position = {
                    'lat': request.user.location.position.latitude,
                    'lon': request.user.location.position.longitude
                }
            elif request.user.place and request.user.place.position:
                position = {
                    'lat': request.user.place.position.latitude,
                    'lon': request.user.place.position.longitude
                }

            if position:
                score = score | FunctionScore(
                    score_mode='first',
                    functions=[
                        SF({
                            'filter': {'exists': {'field': 'position'}},
                            'weight': 0.1,
                            'gauss': {
                                'position': {
                                    'origin': position,
                                    'scale': "100km"
                                },
                                'multi_value_mode': 'max',
                            },
                        }),
                        SF({'weight': 0}),
                    ]
                )

        return score

    def get_date_filter(self, value, request):
        date = dateutil.parser.parse(value).date()
        start = date.replace(date.year, date.month, 1)
        end = start + dateutil.relativedelta.relativedelta(day=31)
        return Range(date={'gt': start, 'lt': end}) | Range(deadline={'gt': start})

    def get_default_filters(self, request):
        return [Terms(review_status=['approved']), ~Term(status='closed')]
