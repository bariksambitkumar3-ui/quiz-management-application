from django.contrib import admin
from . import models
for m in (models.User, models.SchoolClass, models.Subject, models.SchoolSettings, models.Quiz, models.Attempt):
    admin.site.register(m)
