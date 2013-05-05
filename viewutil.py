import re;
from tracker.models import *;

# Adapted from http://djangosnippets.org/snippets/1474/

def get_referer_site(request):
  origin = request.META.get('HTTP_ORIGIN', None);
  if origin != None:
    return re.sub('^https?:\/\/', '', origin);
  else:
    return None;
    
def get_event(event):
	if event:
		if re.match('^\d+$', event):
			event = int(event)
			return Event.objects.get(id=event)
		else:
			eventSet = Event.objects.filter(short=event);
			if eventSet.exists():
				return eventSet[0];
			else:
				raise Http404;	
	e = Event()
	e.id = '' 
	e.name = 'All Events'
	return e
