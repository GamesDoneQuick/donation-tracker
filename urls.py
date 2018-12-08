from django.conf.urls import include, url

from .views import public, api, donateviews, user, auth

from .ui import urls as ui_urls

app_name = 'tracker'
urlpatterns = [
    url(r'^ui/', include(ui_urls, namespace='ui')),
    url(r'^i18n/', include('django.conf.urls.i18n', namespace='i18n')),

    url(r'^bids/(?P<event>\w+|)$', public.bidindex, name='bidindex'),
    url(r'^bid/(?P<id>-?\d+)$', public.bid, name='bid'),
    url(r'^donors/(?P<event>\w+|)$', public.donorindex, name='donorindex'),
    url(r'^donor/(?P<id>-?\d+)$', public.donor, name='donor'),
    url(r'^donor/(?P<id>-?\d+)/(?P<event>\w*)$', public.donor, name='donor'),
    url(r'^donations/(?P<event>\w+|)$',
        public.donationindex, name='donationindex'),
    url(r'^donation/(?P<id>-?\d+)$', public.donation, name='donation'),
    url(r'^runs/(?P<event>\w+|)$', public.runindex, name='runindex'),
    url(r'^run/(?P<id>-?\d+)$', public.run, name='run'),
    url(r'^prizes/(?P<event>\w+|)$', public.prizeindex, name='prizeindex'),
    url(r'^prize/(?P<id>-?\d+)$', public.prize, name='prize'),
    url(r'^events/$', public.eventlist, name='eventlist'),
    url(r'^index/(?P<event>\w+|)$', public.index, name='index'),
    # unfortunately, using the 'word' variant here clashes with the admin site (not to mention any unparameterized urls), so I guess its going to have to be this way for now.  I guess that ideally, one would only use the 'index' url, and redirect to it as neccessary).
    url(r'^(?P<event>\d+|)$', public.index),

    url(r'^donate/(?P<event>\w+)$', donateviews.donate, name='donate'),
    url(r'^paypal_return/$', donateviews.paypal_return, name='paypal_return'),
    url(r'^paypal_cancel/$', donateviews.paypal_cancel, name='paypal_cancel'),
    url(r'^ipn/$', donateviews.ipn, name='ipn'),

    url(r'^prize_donors$', api.prize_donors),
    url(r'^draw_prize$', api.draw_prize),
    url(r'^search/$', api.search),
    url(r'^add/$', api.add),
    url(r'^edit/$', api.edit),
    url(r'^delete/$', api.delete),
    url(r'^command/$', api.command),
    url(r'^me/$', api.me),
    url(r'^api/v1/$', api.api_v1, name='api_v1'),
    url(r'^api/v1/search/$', api.search),
    url(r'^api/v1/add/$', api.add),
    url(r'^api/v1/edit/$', api.edit),
    url(r'^api/v1/delete/$', api.delete),
    url(r'^api/v1/command/$', api.command),
    url(r'^api/v1/me/$', api.me),
    url(r'^api/v2/', include('tracker.api.urls')),

    url(r'^user/index/$', user.user_index, name='user_index'),
    url(r'^user/user_prize/(?P<prize>\d+)$',
        user.user_prize, name='user_prize'),
    url(r'^user/prize_winner/(?P<prize_win>\d+)$',
        user.prize_winner, name='prize_winner'),
    url(r'^user/submit_prize/(?P<event>\w+)$',
        user.submit_prize, name='submit_prize'),

    url(r'^user/login/$', auth.login, name='login'),
    url(r'^user/logout/$', auth.logout, name='logout'),
    url(r'^user/password_reset/$', auth.password_reset, name='password_reset'),
    url(r'^user/password_reset_done/$',
        auth.password_reset_done, name='password_reset_done'),
    url(r'^user/password_reset_confirm/$',
        auth.password_reset_confirm, name='password_reset_confirm'),
    url(r'^user/password_reset_complete/$',
        auth.password_reset_complete, name='password_reset_complete'),
    url(r'^user/password_change/$', auth.password_change, name='password_change'),
    url(r'^user/password_change_done/$',
        auth.password_change_done, name='password_change_done'),
    url(r'^user/register/$', auth.register, name='register'),
    url(r'^user/confirm_registration/$',
        auth.confirm_registration, name='confirm_registration'),
]
