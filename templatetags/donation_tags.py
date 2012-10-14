from django import template
from donations import settings
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
import datetime
import locale

register = template.Library()

def sortlink(sort, order, page, style, contents):
	def getPage(page):
		if page == 'full':
			return '&amp;full'
		elif int(page) < 2: 
			return ''
		return '&amp;page=%d' % int(page)
	if style:
		return '<a href="?sort=%s&amp;order=%s%s" class="%s"><span style="display:none;">%s</span></a>' % (sort,order,getPage(page),style,contents)
	else:
		return '<a href="?sort=%s&amp;order=%s%s">%s</a>' % (sort,order,getPage(page),contents)

@register.tag("sort")
def do_sort(parser, token):
	class SortParser(template.TokenParser):
		def sortParse(self):
			if not self.more():
				raise ValueError
			sort_field = self.value()
			page = None
			if self.more():
				page = self.tag()
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
			self.page = template.Variable(page)
	def render(self, context):
		page = getattr(self, 'page', 1)
		if page != 1:
			page = page.resolve(context)
		return sortlink(self.sort, 1, page, 'asc', 'Asc') + sortlink(self.sort, -1, page, 'dsc', 'Dsc')

@register.tag("pagefirst")
@register.tag("pagefull")
def do_pageff(parser, token):
	try:
		tag_name, sort, order = token.split_contents()
	except ValueError:
		raise template.TemplateSyntaxError('%r tag requires two arguments' % token.contents.split()[0])
	return PageFLFNode(tag_name, sort, order)
	
@register.tag("pagelast")
def do_pagel(parser, token):
	try:
		tag_name, sort, order, num = token.split_contents()
	except ValueError:
		raise template.TemplateSyntaxError('%r tag requires three arguments' % token.contents.split()[0])
	return PageFLFNode(tag_name, sort, order, num)

class PageFLFNode(template.Node):
	def __init__(self, tag, sort, order, num='page'):
		self.tag = tag
		self.sort = template.Variable(sort)
		self.order = template.Variable(order)
		self.num = template.Variable(num)
	def render(self, context):
		sort = self.sort.resolve(context)
		order = self.order.resolve(context)
		if self.tag == 'pagefirst':
			return sortlink(sort, order, 1, 'first', '|&lt; ')
		elif self.tag == 'pagelast':
			num = self.num.resolve(context)
			return sortlink(sort, order, num, 'last', '&gt;| ')
		elif self.tag == 'pagefull':
			return sortlink(sort, order, 'full', None, 'View Full List')
	
@register.tag("pageprev")
@register.tag("pagenext")
def do_pagepn(parser, token):
	try:
		tag_name, sort, order, has, page = token.split_contents()
	except ValueError:
		raise template.TemplateSyntaxError('%r tag requires four arguments' % token.contents.split()[0])
	return PagePNNode(tag_name, sort, order, has, page)

class PagePNNode(template.Node):
	dc = { 'pageprev' : '< ', 'pagenext' : '> ' }
	def __init__(self, tag, sort, order, has, page):
		self.tag = tag
		self.sort = template.Variable(sort)
		self.order = template.Variable(order)
		self.has = template.Variable(has)
		self.page = template.Variable(page)
	def render(self, context):
		has = self.has.resolve(context)
		if has:
			sort = self.sort.resolve(context)
			order = self.order.resolve(context)
			page = self.page.resolve(context)
			return sortlink(sort, order, page, self.tag[4:], PagePNNode.dc[self.tag])
		return ''
	
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
			
@register.tag("name")
def do_name(parser, token):
	class NameParser(template.TokenParser):
		def nameParse(self):
			first = self.value()
			if not self.more(): raise ValueError
			last = self.tag()
			if not self.more(): raise ValueError
			show = self.tag()
			if self.more(): raise ValueError
			return first, last, show
	try:
		first_name, last_name, show = NameParser(token.contents).nameParse()
	except ValueError:
		raise template.TemplateSyntaxError(u'"%s" tag requires three arguments' % token.contents.split()[0])
	return NameNode(parser.compile_filter(first_name), parser.compile_filter(last_name), parser.compile_filter(show))
	
class NameNode(template.Node):
	def __init__(self,first_name,last_name,show):
		if isinstance(first_name.var, basestring):
			first_name.var = template.Variable(u"'%s'" % first_name.var)
		self.first_name = first_name
		if isinstance(last_name.var, basestring):
			last_name.var = template.Variable(u"'%s'" % last_name.var)
		self.last_name = last_name
		if isinstance(show.var, basestring):
			show.var = template.Variable(u"'%s'" % show.var)
		self.show = show
	def render(self, context):
		try:
			show = self.show.resolve(context)
			first_name = self.first_name.resolve(context)
			last_name = self.last_name.resolve(context)
			if not show:
				last_name = last_name[:1] + u'...'
			return last_name + u', ' + first_name
		except (template.VariableDoesNotExist, TypeError), e:
			return ''
			
@register.tag("email")
def do_email(parser, token):
	class EmailParser(template.TokenParser):
		def emailParse(self):
			email = self.value()
			show = True
			if self.more():
				show = self.tag()
			surround = None
			if self.more():
				surround = self.tag()
				if self.more(): raise ValueError
			return email,show,surround
	try:
		email,show,surround = EmailParser(token.contents).emailParse()
	except ValueError:
		raise template.TemplateSyntaxError(u'"%s" tag requires one to three arguments' % token.contents.split()[0])
	if surround:
		if not (surround[0] == surround[-1] and surround[0] in ('"', "'")):
			raise template.TemplateSyntaxError("%s tag's third argument should be in quotes" % token.contents.split()[0])
		if '.' not in surround:
			raise template.TemplateSyntaxError("%s tag's third argument should have a '.' separator dot in" % token.contents.split()[0])		
		surround = surround[1:-1]
	if type(show) != type(True):
		show = parser.compile_filter(show)
	return EmailNode(parser.compile_filter(email), show, surround)

class EmailNode(template.Node):
	def __init__(self,email,show,surround):
		if isinstance(email.var, basestring):
			email.var = template.Variable(u"'%s'" % email.var)
		self.email = email
		if hasattr(show, 'var') and isinstance(show.var, basestring):
			show.var = template.Variable(u"'%s'" % show.var)
		self.show = show
		self.surround = surround
	def render(self,context):
		try:
			email = self.email.resolve(context)
			if hasattr(self.show, 'var'):
				show = self.show.resolve(context)
			else:
				show = self.show
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
