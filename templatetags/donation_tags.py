from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.core.exceptions import ImproperlyConfigured

import datetime
import locale
import urllib

register = template.Library()

def tryresolve(var, context, default=None):
  try:
    return var.resolve(context)
  except template.VariableDoesNotExist:
    return default

def sortlink(style, contents, **args):
  args = filter(lambda i: i[1], args.items())
  ret = []
  ret.append('<a href="?')
  ret.append(conditional_escape(urllib.urlencode(args)))
  ret.append('"')
  if style: ret.append(' class="%s"' % style)
  ret.append('>')
  if style: ret.append('<span style="display:none;">')
  ret.append(contents)
  if style: ret.append('</span>')
  ret.append('</a>')
  return ''.join(map(unicode,ret))

@register.tag("sort")
def do_sort(parser, token):
  class SortParser(template.TokenParser):
    def sortParse(self):
      if not self.more():
        raise ValueError
      sort_field = self.value()
      page = None
      if self.more():
        page = template.Variable(self.tag())
      if self.more():
        raise ValueError
      return sort_field,page
  try:
    sort_field,page = SortParser(token.contents).sortParse()
  except ValueError:
    raise template.TemplateSyntaxError('%r tag requires either one or two arguments' % token.contents.split()[0])
  if not (sort_field[0] == sort_field[-1] and sort_field[0] in ('"', "'")):
    raise template.TemplateSyntaxError("%r tag's first argument should be in quotes" % token.contents.split()[0])
  return SortNode(sort_field[1:-1],page)

class SortNode(template.Node):
  def __init__(self, sort, page):
    self.sort = sort
    if page:
      self.page = page
      self.request = None
    else:
      self.request = template.Variable('request')
  def render(self, context):
    if self.request:
      try:
        request = self.request.resolve(context)
      except template.VariableDoesNotExist:
        raise ImproperlyConfigured('Couldn\'t resolve request variable, is the appropriate context processor included?')
      try:
        self.page = template.Variable(unicode(int(request.GET.get('page', '1'))))
      except ValueError:
        self.page = template.Variable('1')
    page = self.page.resolve(context)
    return sortlink('asc', 'Asc', sort=self.sort, order=1, page=page) + sortlink('dsc', 'Dsc', sort=self.sort, order=-1, page=page)

@register.tag("pagefirst")
@register.tag("pagefull")
def do_pageff(parser, token):
  try:
    tag_name, = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError('%r tag takes no arguments' % token.contents.split()[0])
  return PageFLFNode(tag_name)
  
@register.tag("pagelast")
def do_pagel(parser, token):
  try:
    tag_name, page = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError('%r tag takes one argument' % token.contents.split()[0])
  return PageFLFNode(tag_name, page)

class PageFLFNode(template.Node):
  def __init__(self, tag, page='request.GET.page'):
    self.tag = tag
    self.page = template.Variable(page)
  def render(self, context):
    sort = tryresolve(template.Variable('request.GET.sort'),context)
    order = tryresolve(template.Variable('request.GET.order'),context)
    if self.tag == 'pagefirst':
      return sortlink('first', '|&lt; ', sort=sort, order=order, page=1)
    elif self.tag == 'pagelast':
      page = self.page.resolve(context)
      return sortlink('last', '&gt;| ', sort=sort, order=order, page=page)
    elif self.tag == 'pagefull':
      return sortlink(None, 'View Full List', sort=sort, order=order, page='full')
  
@register.tag("pageprev")
@register.tag("pagenext")
def do_pagepn(parser, token):
  try:
    tag_name, page = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError('%r tag requires one argument' % token.contents.split()[0])
  return PagePNNode(tag_name, page)

class PagePNNode(template.Node):
  dc = { 'pageprev' : '< ', 'pagenext' : '> ' }
  def __init__(self, tag, page):
    self.tag = tag
    self.page = template.Variable(page)
  def render(self, context):
    sort = tryresolve(template.Variable('request.GET.sort'),context)
    order = tryresolve(template.Variable('request.GET.order'),context)
    page = self.page.resolve(context)
    return sortlink(self.tag[4:], PagePNNode.dc[self.tag], sort=sort, order=order, page=page)
    
@register.tag("pagelink")
def do_pagelink(parser, token):
  try:
    tag_name, page = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError('%r tag requires one argument' % token.contents.split()[0])
  return PageLinkNode(tag_name, page)
  
class PageLinkNode(template.Node):
  def __init__(self, tag, page):
    self.tag = tag
    self.page = template.Variable(page)
  def render(self, context):
    sort = tryresolve(template.Variable('request.GET.sort'),context)
    order = tryresolve(template.Variable('request.GET.order'),context)
    page = self.page.resolve(context)
    return sortlink('', page, sort=sort, order=order, page=page)
    
@register.tag("datetime")
def do_datetime(parser, token):
  try:
    tag_name, date = token.split_contents();
  except ValueError:
    raise template.TemplateSyntaxError('%r tag requires one argument' % token.contents.split()[0]);
  return DateTimeNode(tag_name, date);

class DateTimeNode(template.Node):
  def __init__(self, tag, date):
    self.tag = tag
    self.date = template.Variable(date)
  def render(self, context):
    date = self.date.resolve(context)
    return '<span class="datetime">' + date.strftime('%m/%d/%Y %H:%M:%S') + ' +0000</span>';

@register.tag("rendertime")
def do_rendertime(parser, token):
  try:
    tag_name, time = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError('%r tag requires a single argument' % token.contents.split()[0])
  return RenderTimeNode(time)
  
class RenderTimeNode(template.Node):
  def __init__(self, time):
    self.time = template.Variable(time)
  def render(self, context):
    try:
      time = self.time.resolve(context)
      try:
        now = datetime.datetime.now() - time
      except TypeError:
        return ''
      return '%d.%d seconds' % (now.seconds,now.microseconds)
    except template.VariableDoesNotExist:
      return ''

@register.tag("bid")
def do_bid(parser, token):
  try:
    bid = template.TokenParser(token.contents).value();
  except ValueError:
    raise template.TemplateSyntaxError(u'"%s" tag requires one argument' % token.contents.split()[0])
  return BidNode(parser.compile_filter(bid));

class BidNode:
  def __init__(self, bidTok):
    if isinstance(bidTok.var, basestring):
      bidTok.var = template.Variable(u"'%s'" % bidTok.var);
    self.bidTok = bidTok;
  def render(self, context):
    try:
      bid = self.bidTok.resolve(context);
      return '';
    except (template.VariableDoesNotExist, TypeError), e:
      return '';
      
  
@register.tag("name")
def do_name(parser, token):
  class NameParser(template.TokenParser):
    def nameParse(self):
      donor = self.value()
      return donor
  try:
    donor = NameParser(token.contents).nameParse()
  except ValueError:
    raise template.TemplateSyntaxError(u'"%s" tag requires one argument' % token.contents.split()[0])
  return NameNode(parser.compile_filter(donor))
  
class NameNode(template.Node):
  def __init__(self,donor):
    if isinstance(donor.var, basestring):
      donor.var = template.Variable(u"'%s'" % donor.var)
    self.donor = donor
  def render(self, context):
    try:
      donor = self.donor.resolve(context)
      visibility = donor.visibility;
      show = template.Variable(u'perms.tracker.view_usernames').resolve(context)
      alias = donor.alias;
      if visibility == 'ANON' and not show:
        return 'Anonymous'
      elif visibility == 'ALIAS' and not show:
        return alias;
      last_name,first_name = donor.lastname,donor.firstname
      # I need to go through and cleanup all of the current donors to be either anonymous, alias, or full if they are okay with it.
      if not show:
        last_name = last_name[:1] + u'...'
      if not last_name and not first_name:
        return '(No Name)' if alias == None else alias;
      else:
        return last_name + u', ' + first_name + ('' if alias == None else ' (' + alias + ')');
    except (template.VariableDoesNotExist, TypeError), e:
      return ''
      
@register.tag("email")
def do_email(parser, token):
  class EmailParser(template.TokenParser):
    def emailParse(self):
      email = self.value()
      surround = None
      if self.more():
        surround = self.tag()
        if self.more(): raise ValueError
      return email,surround
  try:
    email,surround = EmailParser(token.contents).emailParse()
  except ValueError:
    raise template.TemplateSyntaxError(u'"%s" tag requires one or two arguments' % token.contents.split()[0])
  if surround:
    if not (surround[0] == surround[-1] and surround[0] in ('"', "'")):
      raise template.TemplateSyntaxError("%s tag's second argument should be in quotes" % token.contents.split()[0])
    if '.' not in surround:
      raise template.TemplateSyntaxError("%s tag's second argument should have a '.' separator dot in" % token.contents.split()[0])    
    surround = surround[1:-1]
  return EmailNode(parser.compile_filter(email), surround)

class EmailNode(template.Node):
  def __init__(self,email,surround):
    if isinstance(email.var, basestring):
      email.var = template.Variable(u"'%s'" % email.var)
    self.email = email
    self.surround = surround
  def render(self,context):
    try:
      email = self.email.resolve(context)
      show = template.Variable(u'perms.tracker.view_emails').resolve(context)
      left,right = '',''
      if self.surround:
        left,right = self.surround.split('.')
      if show:
        return '%s<a href="mailto:%s">%s</a>%s' % (left, email, email, right)
      else:
        return ''
    except (template.VariableDoesNotExist, TypeError), e:
      return ''
      
@register.filter
#@stringfilter
def forumfilter(value,autoescape=None):
  if autoescape:
    esc = conditional_escape
  else:
    esc = lambda x: x
  return mark_safe(esc(value).replace('\n', '<br />'))
forumfilter.is_safe = True
forumfilter.needs_autoescape = True

@register.filter
def money(value):
  locale.setlocale( locale.LC_ALL, '')
  try:
    if not value:
      return locale.currency(0.0)
    return locale.currency(value, symbol=True, grouping=True)
  except ValueError:
    locale.setlocale( locale.LC_MONETARY, ('en', 'us'))
    if not value:    
      return locale.currency(0.0)
    return locale.currency(value, symbol=True, grouping=True)
money.is_safe = True

@register.filter("abs")
def filabs(value,arg):
  try:
    return abs(int(value)-int(arg))
  except ValueError:
    raise template.TemplateSyntaxError('abs requires integer arguments')

@register.filter("mod")
def filmod(value,arg):
  try:
    return int(value) % int(arg)
  except ValueError:
    raise template.TemplateSyntaxError('mod requires integer arguments')

@register.filter("negate")
def negate(value):
  return not value;
    
@register.simple_tag
def bid_event(bid):
  return bid.event if bid.event else bid.speedrun.event;
    
@register.simple_tag
def bid_short_cached(bid, cache=None, showEvent=False, showRun=False, showOptions=False, addTable=True, showMain=True):
  options = [];
  if showOptions:
    if cache:
      bid = cache[bid.id];
    options = list(bid.options.all());
  event = None;
  if showEvent:
    event = bid.event if bid.event else bid.speedrun.event;
  bidNameSpan = 1;
  if not showEvent:
    bidNameSpan += 1;
  if not bid.speedrun:
    showRun = False;
  if not showRun:
    bidNameSpan += 1;
  return template.loader.render_to_string('tracker/bidshort.html', { 'bid': bid, 'event': event, 'options': options, 'bidNameSpan': bidNameSpan, 'cache': cache, 'showEvent': showEvent, 'showRun': showRun, 'addTable': addTable, 'showOptions': showOptions, 'showMain': showMain });
  
@register.simple_tag
def bid_short(bid, **kwargs):
  return bid_short_cached(bid, cache=None, **kwargs);
  
