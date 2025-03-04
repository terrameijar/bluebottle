from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import PasswordResetDoneView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.views.generic import RedirectView

from bluebottle.views import HomeView
from bluebottle.auth.views import admin_password_reset
from bluebottle.bluebottle_dashboard.views import locked_out
from bluebottle.looker.dashboard_views import LookerEmbedView  # noqa This has to be imported early so that custom urls will work


admin.autodiscover()


urlpatterns = [

    # Django JET URLS
    url(r'^admin/jet/', include('jet.urls', 'jet')),
    url(r'^admin/jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),

    url(r'^admin/locked/$', locked_out, name='admin-locked-out'),
    # Django Admin, docs and password reset
    url(r'^admin/password_reset/$',
        admin_password_reset,
        name='admin_password_reset'),
    url(r'^admin/password_reset/done/$',
        PasswordResetDoneView.as_view(), name='password_reset_done'),
    url(r'^admin/password_reset/confirm/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'),
    url(r'^admin/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        PasswordResetConfirmView.as_view(),
        {'post_reset_redirect': '/admin'}, name='password_reset_confirm'),
    url(r'^admin/exportdb/', include('bluebottle.exports.urls')),
    url(r'^admin/', admin.site.urls),

    url(r'^admin/utils/tinymce/', include('tinymce.urls')),
    url(r'^admin/utils/admintools/', include('admin_tools.urls')),

    # account login/logout, password reset, and password change
    url(
        r'^accounts/',
        include('django.contrib.auth.urls'),
    ),

    url(r'^admin/summernote/', include('django_summernote.urls')),
    url(r'^admin', RedirectView.as_view(url=reverse_lazy('admin:index')), name='admin-slash'),
    url(r'^', HomeView.as_view(), name='home'),

]
