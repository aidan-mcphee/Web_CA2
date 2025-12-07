from django.shortcuts import render
from rest_framework import viewsets
from rest_framework_gis.filters import InBBoxFilter
from .models import Article
from .serializers import ArticleSerializer

# Page views
def index(request):
    return render(request, 'wikimap/index.html')

def map_view(request):
    return render(request, 'wikimap/map.html')

# API Views
class ArticleViewSet(viewsets.ReadOnlyModelViewSet): # We do not add Articles from frontend
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    bbox_filter_field = 'coordinates' 
    filter_backends = (InBBoxFilter,) # Filter articles based on bounding box
    pagination_class = None
