import post_office

def get_email_template(name, default=None):
    """Get an email template, or fall back to use the default template object (if provided)"""
    try:
        return post_office.models.EmailTemplate.objects.get(name=name)
    except post_office.models.EmailTemplate.DoesNotExist:
        return default

def get_or_create_email_template(name, default):
    "Get an email template, or fall back to creating one, using the provided name onto the default template"""
    # the extra bookkeeping here is to ensure that `default` is not modified as a side-effect
    oldPk = default.pk
    oldId = default.id
    try:
        return post_office.models.EmailTemplate.objects.get(name=name)
    except post_office.models.EmailTemplate.DoesNotExist:
        default.pk = None
        default.id = None
        default.name = name
        default.save()
        return get_email_template(name)
    finally:
        default.pk = oldPk
        default.id = oldId

