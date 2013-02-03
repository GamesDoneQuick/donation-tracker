import re;

# Adapted from http://djangosnippets.org/snippets/1474/

def get_referer_site(request):
  origin = request.META.get('HTTP_ORIGIN', None);
  if origin != None:
    return re.sub('^https?:\/\/', '', origin);
  else:
    return None;

