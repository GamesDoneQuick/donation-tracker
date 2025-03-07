from django.contrib import admin

from tracker import models

from .util import CustomModelAdmin


class AbstractTagAdmin(CustomModelAdmin):
    search_fields = ('name',)


admin.site.register(models.Tag, AbstractTagAdmin)
