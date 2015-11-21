from django.db import models

# This addresses an unexpected issue where accessing a null OneToOneField from its non-defined side
# will throw an error instead of returning null. There seems to be a 7-year long discussion about
# this, so its likely not going to be resolved (especially since its a fairly big backwards compatiblity break)
# This just modifies the access so that it works the way you think it would
# http://stackoverflow.com/questions/3955093/django-return-none-from-onetoonefield-if-related-object-doesnt-exist

class SingleRelatedObjectDescriptorReturnsNone(models.fields.related.SingleRelatedObjectDescriptor):
    def __get__(self, instance, instance_type=None):
        try:
            return super(SingleRelatedObjectDescriptorReturnsNone, self).__get__(instance=instance, instance_type=instance_type)
        except models.ObjectDoesNotExist:
            return None


class OneToOneOrNoneField(models.OneToOneField):
    """A OneToOneField that returns None if the related object doesn't exist"""
    related_accessor_class = SingleRelatedObjectDescriptorReturnsNone
