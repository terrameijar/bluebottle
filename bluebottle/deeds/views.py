import csv

from django.db.models import Q
from django.http import HttpResponse

from bluebottle.activities.permissions import (
    ActivityOwnerPermission, ActivityTypePermission, ActivityStatusPermission,
    DeleteActivityPermission, ContributorPermission, ActivitySegmentPermission
)
from bluebottle.deeds.models import Deed, DeedParticipant
from bluebottle.deeds.serializers import (
    DeedSerializer, DeedTransitionSerializer, DeedParticipantSerializer,
    DeedParticipantTransitionSerializer
)
from bluebottle.segments.views import ClosedSegmentActivityViewMixin
from bluebottle.transitions.views import TransitionList
from bluebottle.utils.admin import prep_field
from bluebottle.utils.permissions import (
    OneOf, ResourcePermission, ResourceOwnerPermission
)
from bluebottle.utils.views import (
    RetrieveUpdateDestroyAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateAPIView,
    JsonApiViewMixin, PrivateFileView, IcalView
)


class DeedListView(JsonApiViewMixin, ListCreateAPIView):
    queryset = Deed.objects.all()
    serializer_class = DeedSerializer

    permission_classes = (
        ActivityTypePermission,
        OneOf(ResourcePermission, ActivityOwnerPermission),
    )

    def perform_create(self, serializer):
        self.check_related_object_permissions(
            self.request,
            serializer.Meta.model(**serializer.validated_data)
        )

        self.check_object_permissions(
            self.request,
            serializer.Meta.model(**serializer.validated_data)
        )
        serializer.save(owner=self.request.user)


class DeedDetailView(JsonApiViewMixin, ClosedSegmentActivityViewMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = (
        ActivityStatusPermission,
        OneOf(ResourcePermission, ActivityOwnerPermission),
        ActivitySegmentPermission,
        DeleteActivityPermission
    )

    queryset = Deed.objects.all()
    serializer_class = DeedSerializer


class DeedTransitionList(TransitionList):
    serializer_class = DeedTransitionSerializer
    queryset = Deed.objects.all()


class DeedRelatedParticipantList(JsonApiViewMixin, ListAPIView):
    permission_classes = (
        OneOf(ResourcePermission, ResourceOwnerPermission),
    )
    pagination_class = None

    queryset = DeedParticipant.objects.prefetch_related('user')
    serializer_class = DeedParticipantSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = self.queryset.filter(
                Q(user=self.request.user) |
                Q(activity__owner=self.request.user) |
                Q(activity__initiative__activity_manager=self.request.user) |
                Q(status__in=('accepted', 'succeeded', ))
            )
        else:
            queryset = self.queryset.filter(
                status__in=('accepted', 'succeeded', )
            )

        return queryset.filter(
            activity_id=self.kwargs['activity_id']
        )


class ParticipantList(JsonApiViewMixin, ListCreateAPIView):
    permission_classes = (
        OneOf(ResourcePermission, ResourceOwnerPermission),
    )
    queryset = DeedParticipant.objects.all()
    serializer_class = DeedParticipantSerializer

    def perform_create(self, serializer):
        self.check_related_object_permissions(
            self.request,
            serializer.Meta.model(**serializer.validated_data)
        )

        self.check_object_permissions(
            self.request,
            serializer.Meta.model(**serializer.validated_data)
        )

        serializer.save(user=self.request.user)


class ParticipantDetail(JsonApiViewMixin, RetrieveUpdateAPIView):
    permission_classes = (
        OneOf(ResourcePermission, ResourceOwnerPermission, ContributorPermission),
    )
    queryset = DeedParticipant.objects.all()
    serializer_class = DeedParticipantSerializer


class ParticipantTransitionList(TransitionList):
    serializer_class = DeedParticipantTransitionSerializer
    queryset = DeedParticipant.objects.all()


class ParticipantExportView(PrivateFileView):
    fields = (
        ('user__email', 'Email'),
        ('user__full_name', 'Name'),
        ('created', 'Registration Date'),
        ('status', 'Status'),
    )

    model = Deed

    def get(self, request, *args, **kwargs):
        activity = self.get_object()

        response = HttpResponse()
        response['Content-Disposition'] = 'attachment; filename="participants.csv"'
        response['Content-Type'] = 'text/csv'

        writer = csv.writer(response)

        row = [field[1] for field in self.fields]
        writer.writerow(row)

        for participant in activity.contributors.instance_of(
            DeedParticipant
        ):
            row = [prep_field(request, participant, field[0]) for field in self.fields]
            writer.writerow(row)

        return response


class DeedIcalView(IcalView):
    queryset = Deed.objects.exclude(
        status__in=['cancelled', 'deleted', 'rejected'],
    )
