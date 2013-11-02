#http://stackoverflow.com/questions/4557114/django-custom-template-tag-which-accepts-a-boolean-parameter

# It came up that I needed true/false values in the templates, 0/1 works, but I like having symbolic names
def booleans(request):
    return {
        'True': True,
        'False': False,
    }