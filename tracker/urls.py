import paypal.standard.ipn.views
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
from django.urls import include, reverse_lazy, path
from tracker import api_urls
from tracker.feeds.runs_calendar import RunsCalendar
from tracker.ui import urls as ui_urls
from tracker.views import public, api, donateviews, user, auth

app_name = 'tracker'
urlpatterns = [
    path('', public.index, name='index_all'),
    path('ui/', include(ui_urls, namespace='ui')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('bids/<slug:event>', public.bidindex, name='bidindex'),
    path('bids/', public.bidindex, name='bidindex'),
    path('bid/<int:pk>', public.bid_detail, name='bid'),
    path('donors/<slug:event>', public.donorindex, name='donorindex'),
    path('donors/', public.donorindex, name='donorindex'),
    path('donor/<int:pk>/<slug:event>', public.donor_detail, name='donor'),
    path('donor/<int:pk>', public.donor_detail, name='donor'),
    path('donations/<slug:event>', public.donationindex, name='donationindex'),
    path('donations/', public.donationindex, name='donationindex'),
    path('donation/<int:pk>', public.donation_detail, name='donation'),
    path('runs/<slug:event>', public.runindex, name='runindex'),
    path('runs/', public.runindex, name='runindex'),
    path('run/<int:pk>', public.run_detail, name='run'),
    path('prizes/<slug:event>', public.prizeindex, name='prizeindex'),
    path('prizes/', public.prizeindex, name='prizeindex'),
    path('prize/<int:pk>', public.prize_detail, name='prize'),
    path('events/<slug:event>/calendar', RunsCalendar(), name='calendar'),
    path('events/', public.eventlist, name='eventlist'),
    path('event/<slug:event>', public.index, name='index'),
    path('donate/<slug:event>', donateviews.donate, name='donate'),
    path('paypal_return/', donateviews.paypal_return, name='paypal_return'),
    path('paypal_cancel/', donateviews.paypal_cancel, name='paypal_cancel'),
    path('ipn/', paypal.standard.ipn.views.ipn, name='ipn'),
    path('search/', api.search),
    path('add/', api.add),
    path('edit/', api.edit),
    path('delete/', api.delete),
    path('command/', api.command),
    path('me/', api.me, name='me'),
    path('api/v1/', include(api_urls, namespace='api_v1')),
    path('api/v2/', include('tracker.api.urls')),
    path('user/index/', user.user_index, name='user_index'),
    path('user/user_prize/<int:prize>', user.user_prize, name='user_prize'),
    path('user/prize_winner/<int:prize_win>', user.prize_winner, name='prize_winner',),
    path('user/submit_prize/<slug:event>', user.submit_prize, name='submit_prize'),
    path('user/register/', auth.register, name='register'),
    path(
        'user/confirm_registration/<uidb64>/<token>/',
        auth.confirm_registration,
        name='confirm_registration',
    ),
    # all urls below are served by standard Django views
    path(
        'user/login/',
        LoginView.as_view(template_name='tracker/login.html'),
        name='login',
    ),
    path('user/logout/', LogoutView.as_view(next_page='tracker:login'), name='logout',),
    path(
        'user/password_reset/',
        PasswordResetView.as_view(
            template_name='tracker/password_reset.html',
            email_template_name='tracker/email/password_reset.txt',
            html_email_template_name='tracker/email/password_reset.html',
            success_url=reverse_lazy('tracker:password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'user/password_reset_done/',
        PasswordResetDoneView.as_view(template_name='tracker/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'user/password_reset_confirm/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(
            template_name='tracker/password_reset_confirm.html',
            success_url=reverse_lazy('tracker:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'user/password_reset_complete/',
        PasswordResetCompleteView.as_view(
            template_name='tracker/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
    path(
        'user/password_change/',
        PasswordChangeView.as_view(
            template_name='tracker/password_change.html',
            success_url=reverse_lazy('tracker:password_change_done'),
        ),
        name='password_change',
    ),
    path(
        'user/password_change_done/',
        PasswordChangeDoneView.as_view(
            template_name='tracker/password_change_done.html'
        ),
        name='password_change_done',
    ),
]
