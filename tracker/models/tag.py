from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.db import models


class TagManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name.lower())

    def get_or_create_by_natural_key(self, name):
        return self.get_or_create(name=name.lower())


class AbstractTag(models.Model):
    name = models.CharField(
        unique=True,
        max_length=32,
        error_messages={'unique': 'Tags must be case-insensitively unique.'},
        validators=[validate_slug],
    )
    objects = TagManager()

    class Meta:
        abstract = True

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)
        exclude = exclude or []
        if (
            'name' not in exclude
            and type(self)
            .objects.exclude(id=self.id)
            .filter(name=self.name.lower())
            .exists()
        ):
            raise ValidationError(
                {'name': self.unique_error_message(type(self), ['name'])}
            )

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        return super().save(*args, **kwargs)

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name


class Tag(AbstractTag):
    # TODO: efficient way to get ads/interviews via reverse lookup? right now it's just the bare interstitial models

    pass
