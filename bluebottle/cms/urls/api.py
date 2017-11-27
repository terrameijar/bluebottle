from django.conf.urls import url

from bluebottle.cms.views import ResultPageDetail, HomePageDetail

urlpatterns = [
    url(r'^results/(?P<pk>\d+)$', ResultPageDetail.as_view(), name='result-page-detail'),
    url(r'^homepage/$', HomePageDetail.as_view(), {'pk': 1}, name='home-page-detail'),
]
