from django.contrib.gis import admin
from .models import Article
from django.core.management import call_command
from django.contrib import messages
import threading

# Register your models here.

@admin.register(Article)
class ArticleAdmin(admin.GISModelAdmin):
    list_display = ('title', 'oldest_date', 'coordinates')
    search_fields = ('title',)
    list_filter = ('oldest_date',)
