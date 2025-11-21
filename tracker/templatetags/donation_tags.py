import urllib.parse
from decimal import Decimal

from babel import localedata, numbers
from django import template
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

from tracker import settings, viewutil
from tracker.models import DonorCache, Event

register = template.Library()


def tryresolve(var, context, default=None):
    try:
        return var.resolve(context)
    except template.VariableDoesNotExist:
        return default


def sortlink(style, contents, **args):
    return format_html(
        '<a href="?{args}"{style}><span style="display:none;">{contents}</span></a>',
        args=urllib.parse.urlencode([a for a in args.items() if a[1]]),
        style=format_html(' class="{style}"', style=style) if style else '',
        contents=contents,
    )


@register.simple_tag(takes_context=True)
def sort(context, sort_field, page=1):
    return sortlink('asc', 'Asc', sort=sort_field, order=1, page=page) + sortlink(
        'dsc', 'Dsc', sort=sort_field, order=-1, page=page
    )


@register.tag('pagefirst')
@register.tag('pagefull')
def do_pageff(parser, token):
    try:
        (tag_name,) = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag takes no arguments' % token.contents.split()[0]
        )
    return PageFLFNode(tag_name)


@register.tag('pagelast')
def do_pagel(parser, token):
    try:
        tag_name, page = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag takes one argument' % token.contents.split()[0]
        )
    return PageFLFNode(tag_name, page)


class PageFLFNode(template.Node):
    def __init__(self, tag, page='request.GET.page'):
        self.tag = tag
        self.page = template.Variable(page)

    def render(self, context):
        sort = tryresolve(template.Variable('request.GET.sort'), context)
        order = tryresolve(template.Variable('request.GET.order'), context)
        if self.tag == 'pagefirst':
            return sortlink('first', '|< ', sort=sort, order=order, page=1)
        elif self.tag == 'pagelast':
            page = self.page.resolve(context)
            return sortlink('last', '>| ', sort=sort, order=order, page=page)
        elif self.tag == 'pagefull':
            return sortlink(None, 'View Full List', sort=sort, order=order, page='full')


@register.tag('pageprev')
@register.tag('pagenext')
def do_pagepn(parser, token):
    try:
        tag_name, page = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag requires one argument' % token.contents.split()[0]
        )
    return PagePNNode(tag_name, page)


class PagePNNode(template.Node):
    dc = {'pageprev': '< ', 'pagenext': '> '}

    def __init__(self, tag, page):
        self.tag = tag
        self.page = template.Variable(page)

    def render(self, context):
        sort = tryresolve(template.Variable('request.GET.sort'), context)
        order = tryresolve(template.Variable('request.GET.order'), context)
        page = self.page.resolve(context)
        return sortlink(
            self.tag[4:], PagePNNode.dc[self.tag], sort=sort, order=order, page=page
        )


@register.tag('pagelink')
def do_pagelink(parser, token):
    try:
        tag_name, page = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag requires one argument' % token.contents.split()[0]
        )
    return PageLinkNode(tag_name, page)


class PageLinkNode(template.Node):
    def __init__(self, tag, page):
        self.tag = tag
        self.page = template.Variable(page)

    def render(self, context):
        sort = tryresolve(template.Variable('request.GET.sort'), context)
        order = tryresolve(template.Variable('request.GET.order'), context)
        page = self.page.resolve(context)
        return sortlink('', page, sort=sort, order=order, page=page)


@register.filter
def forumfilter(value, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:

        def esc(x):
            return x

    return mark_safe(esc(value).replace('\n', '<br />'))


forumfilter.is_safe = True
forumfilter.needs_autoescape = True


@register.simple_tag
def money(cfg: DonorCache | Event | str, value: str | float | Decimal):
    code = settings.LANGUAGE_CODE
    currency = 'UNK'
    if isinstance(cfg, str):
        currency = cfg
    if isinstance(cfg, DonorCache):
        # use the currency if available, else fall back to the event
        currency = cfg.currency
        cfg = cfg.event
    if isinstance(cfg, Event):
        code = cfg.locale_code or code
        currency = cfg.paypalcurrency
    code = localedata.normalize_locale(code.replace('-', '_'))
    return numbers.format_currency(value, currency=currency, locale=code)


money.is_safe = True


@register.filter('abs')
def filabs(value, arg):
    try:
        return abs(int(value) - int(arg))
    except ValueError:
        raise template.TemplateSyntaxError('abs requires integer arguments')


@register.filter('mod')
def filmod(value, arg):
    try:
        return int(value) % int(arg)
    except ValueError:
        raise template.TemplateSyntaxError('mod requires integer arguments')


@register.filter('negate')
def negate(value):
    return not value


@register.simple_tag
def admin_url(obj):
    return viewutil.admin_url(obj)


@register.simple_tag(takes_context=True)
def standardform(
    context, form, formid='formid', submittext='Submit', action=None, showrequired=True
):
    context.push(
        {
            'form': form,
            'formid': formid,
            'submittext': submittext,
            'action': action,
            'showrequired': showrequired,
        }
    )
    return template.loader.render_to_string(
        'standardform.html',
        context.flatten(),
    )


@register.simple_tag
def form_innards(form, showrequired=True):
    return template.loader.render_to_string(
        'form_innards.html',
        {
            'form': form,
            'showrequired': showrequired,
        },
    )
