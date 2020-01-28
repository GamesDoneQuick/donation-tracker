from django.conf.urls import include, url
from django.contrib.auth.views import (
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.urls import reverse_lazy

from tracker import api_urls
from tracker.feeds.runs_calendar import RunsCalendar
from tracker.ui import urls as ui_urls
from tracker.views import public, api, donateviews, user, auth

app_name = 'tracker'
urlpatterns = [
    url(r'^ui/', include(ui_urls, namespace='ui')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^bids/(?P<event>\w+|)$', public.bidindex, name='bidindex'),
    url(r'^bid/(?P<id>-?\d+)$', public.bid, name='bid'),
    url(r'^donors/(?P<event>\w+|)$', public.donorindex, name='donorindex'),
    url(r'^donor/(?P<id>-?\d+)$', public.donor, name='donor'),
    url(r'^donor/(?P<id>-?\d+)/(?P<event>\w*)$', public.donor, name='donor'),
    url(r'^donations/(?P<event>\w+|)$', public.donationindex, name='donationindex'),
    url(r'^donation/(?P<id>-?\d+)$', public.donation, name='donation'),
    url(r'^runs/(?P<event>\w+|)$', public.runindex, name='runindex'),
    url(r'^run/(?P<id>-?\d+)$', public.run, name='run'),
    url(r'^prizes/(?P<event>\w+|)$', public.prizeindex, name='prizeindex'),
    url(r'^prize/(?P<id>-?\d+)$', public.prize, name='prize'),
    url(r'^events/$', public.eventlist, name='eventlist'),
    url(r'^events/(?P<event>\w+)/calendar$', RunsCalendar(), name='calendar'),
    url(r'^event/(?P<event>\w+)$', public.index, name='index'),
    url(r'^$', public.index, name='index_all'),
    url(r'^donate/(?P<event>\w+)$', donateviews.donate, name='donate'),
    url(r'^paypal_return/$', donateviews.paypal_return, name='paypal_return'),
    url(r'^paypal_cancel/$', donateviews.paypal_cancel, name='paypal_cancel'),
    url(r'^ipn/$', donateviews.ipn, name='ipn'),
    url(r'^search/$', api.search),
    url(r'^add/$', api.add),
    url(r'^edit/$', api.edit),
    url(r'^delete/$', api.delete),
    url(r'^command/$', api.command),
    url(r'^me/$', api.me, name='me'),
    url(r'^api/v1/', include(api_urls, namespace='api_v1')),
    url(r'^api/v2/', include('tracker.api.urls')),
    url(r'^user/index/$', user.user_index, name='user_index'),
    url(r'^user/user_prize/(?P<prize>\d+)$', user.user_prize, name='user_prize'),
    url(
        r'^user/prize_winner/(?P<prize_win>\d+)$',
        user.prize_winner,
        name='prize_winner',
    ),
    url(r'^user/submit_prize/(?P<event>\w+)$', user.submit_prize, name='submit_prize'),
    url(r'^user/register/$', auth.register, name='register'),
    url(
        r'^user/confirm_registration/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth.confirm_registration,
        name='confirm_registration',
    ),
    # all urls below are served by standard Django views
    url(
        r'^user/login/$',
        LoginView.as_view(template_name='tracker/login.html'),
        name='login',
    ),
    url(
        r'^user/logout/$', LogoutView.as_view(next_page='tracker:login'), name='logout',
    ),
    url(
        r'^user/password_reset/$',
        PasswordResetView.as_view(
            template_name='tracker/password_reset.html',
            email_template_name='tracker/email/password_reset.html',
            success_url=reverse_lazy('tracker:password_reset_done'),
        ),
        name='password_reset',
    ),
    url(
        r'^user/password_reset_done/$',
        PasswordResetDoneView.as_view(template_name='tracker/password_reset_done.html'),
        name='password_reset_done',
    ),
    url(
        r'^user/password_reset_confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        PasswordResetConfirmView.as_view(
            template_name='tracker/password_reset_confirm.html',
            success_url=reverse_lazy('tracker:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    url(
        r'^user/password_reset_complete/$',
        PasswordResetCompleteView.as_view(
            template_name='tracker/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
    url(
        r'^user/password_change/$',
        PasswordChangeView.as_view(
            template_name='tracker/password_change.html',
            success_url=reverse_lazy('tracker:password_change_done'),
        ),
        name='password_change',
    ),
    url(
        r'^user/password_change_done/$',
        PasswordChangeDoneView.as_view(
            template_name='tracker/password_change_done.html'
        ),
        name='password_change_done',
    ),
]
