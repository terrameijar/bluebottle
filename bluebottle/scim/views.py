from django.contrib.auth.models import Group

from rest_framework import (
    generics, response, permissions, authentication, exceptions
)

from bluebottle.members.models import Member

from bluebottle.scim.models import SCIMPlatformSettings
from bluebottle.scim.serializers import SCIMMemberSerializer, SCIMGroupSerializer
from bluebottle.scim import scim_data


from rest_framework import pagination


class SCIMPaginator(pagination.PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'count'
    page_query_param = 'startIndex'

    def get_paginated_response(self, data):
        return response.Response({
            'totalResults': self.page.paginator.count,
            'startIndex': self.page.number,
            'Resources': data,
            'itemsPerPage': self.page_size,
            'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'],
        })


class SCIMUser(object):
    is_authenticated = True


class SCIMAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        token = SCIMPlatformSettings.objects.get().bearer_token
        if request.META.get('HTTP_AUTHORIZATION') == 'Bearer {}'.format(token):
            return (SCIMUser(), None)

    def authenticate_header(self, request):
        return 'Bearer'


class SCIMViewMixin(object):
    authentication_classes = (SCIMAuthentication, )
    permission_classes = (permissions.IsAuthenticated, )
    pagination_class = SCIMPaginator

    def handle_exception(self, exc):
        try:
            data = {
                'schemas':  ["urn:ietf:params:scim:api:messages:2.0:Error"],
                'status': exc.status_code
            }
        except AttributeError:
            raise exc

        if isinstance(exc.detail, dict):
            data['details'] = '\n'.join(
                '{}: {}'.format(key, ', '.join(value)) for key, value in exc.detail.items()
            )
        else:
            data['details'] = unicode(exc.detail)

        return response.Response(data, status=exc.status_code)


class StaticRetrieveAPIView(SCIMViewMixin, generics.RetrieveAPIView):
    def get(self, request, id):
        self.check_permissions(self.request)
        for item in self.data:
            if item['id'] == id:
                return response.Response(item)

        raise exceptions.NotFound('Resource not found: {}'.format(id))


class StaticListAPIView(SCIMViewMixin, generics.ListAPIView):
    def get(self, request):
        self.paginate_queryset(self.data)
        return self.get_paginated_response(self.data)


class ServiceProviderConfigView(StaticRetrieveAPIView):
    data = scim_data.SERVICE_PROVIDER_CONFIG

    def get(self, request):
        self.check_permissions(self.request)
        return response.Response(self.data)


class SchemaListView(StaticListAPIView):
    data = scim_data.SCHEMAS


class SchemaRetrieveView(StaticRetrieveAPIView):
    data = scim_data.SCHEMAS


class ResourceTypeListView(StaticListAPIView):
    data = scim_data.RESOURCE_TYPES


class ResourceTypeRetrieveView(StaticRetrieveAPIView):
    data = scim_data.RESOURCE_TYPES


class UserListView(SCIMViewMixin, generics.ListCreateAPIView):
    queryset = Member.objects.filter(is_superuser=False)
    serializer_class = SCIMMemberSerializer


class UserDetailView(SCIMViewMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Member.objects.filter(is_superuser=False)
    serializer_class = SCIMMemberSerializer


class GroupListView(SCIMViewMixin, generics.ListAPIView):
    queryset = Group.objects.exclude(name='Authenticated')
    serializer_class = SCIMGroupSerializer


class GroupDetailView(SCIMViewMixin, generics.RetrieveUpdateAPIView):
    queryset = Group.objects.exclude(name='Authenticated')
    serializer_class = SCIMGroupSerializer
