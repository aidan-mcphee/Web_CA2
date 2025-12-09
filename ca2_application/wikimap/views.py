from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from rest_framework import viewsets
from rest_framework_gis.filters import InBBoxFilter
from .models import Article
from .serializers import ArticleSerializer
from django.contrib.gis.db.models.functions import SnapToGrid, Centroid
from django.contrib.gis.db.models.aggregates import Collect
from django.db.models import Count
from django.db.models import Count
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.core.cache import cache
import requests

from urllib.parse import quote
from .models import UserDiscovery
from django.contrib.gis.geos import Point



ZOOM_THRESHOLD = 16

# Page views
def index(request):
    return render(request, 'wikimap/index.html')

def map_view(request):
    return render(request, 'wikimap/map.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def profile(request):
    discoveries = UserDiscovery.objects.filter(user=request.user).select_related('article').order_by('-discovered_at')
    return render(request, 'wikimap/profile.html', {'discoveries': discoveries})


@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been successfully deleted.")
        return redirect('/')
    return redirect('profile')

@api_view(['GET'])
def article_summary(request, title):
    cache_key = f'summary_{title}'
    cached_data = cache.get(cache_key)

    if cached_data:
        return Response(cached_data)

    try:
        # Encode the title for the URL (handles spaces, slashes, etc.)
        encoded_title = quote(title, safe='')
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        response = requests.get(url, headers={'User-Agent': 'WikiMap/1.0 (http://localhost/map/; contact@amcp.ie)'})
        
        if response.status_code == 200:
            data = response.json()
            # Cache for 24 hours
            cache.set(cache_key, data, 60 * 60 * 24)
            return Response(data)
        else:
            return Response({"error": "Failed to fetch summary"}, status=response.status_code)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def search_articles(request):
    query = request.query_params.get('query', '').strip()
    if not query:
        return Response([])
    
    # Case-insensitive containment search, limit to 50 suggestions
    articles = Article.objects.filter(title__icontains=query)[:50]
    serializer = ArticleSerializer(articles, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@login_required
def collect_article(request):
    try:
        article_id = request.data.get('article_id')
        lat = request.data.get('lat')
        lon = request.data.get('lon')

        if not all([article_id, lat, lon]):
            return Response({'error': 'Missing parameters'}, status=400)

        article = Article.objects.get(id=article_id)
        user_point = Point(float(lon), float(lat), srid=4326) # Lon, Lat order
        
        article_point_3857 = article.coordinates.transform(3857, clone=True)
        user_point_3857 = user_point.transform(3857, clone=True)
        distance = article_point_3857.distance(user_point_3857) # meters

        if distance > 2000: # 2km buffer
            return Response({'error': 'You are too far away! Get closer to collect this.'}, status=403)

        # Check if already collected
        if UserDiscovery.objects.filter(user=request.user, article=article).exists():
            return Response({'message': 'Already collected!'}, status=200)

        UserDiscovery.objects.create(user=request.user, article=article)
        return Response({'success': True, 'message': 'Article collected!'}, status=201)

    except Article.DoesNotExist:
        return Response({'error': 'Article not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)



# API Views
class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    bbox_filter_field = 'coordinates' 
    filter_backends = (InBBoxFilter,)
    pagination_class = None

    def get_queryset(self):
        queryset = Article.objects.all()
        min_year = self.request.query_params.get('min_year')
        max_year = self.request.query_params.get('max_year')
        
        if min_year:
            queryset = queryset.filter(oldest_date__year__gte=min_year)
        if max_year:
            queryset = queryset.filter(oldest_date__year__lte=max_year)
            
        return queryset

    def list(self, request, *args, **kwargs):
        zoom = request.query_params.get('zoom')
        if zoom and float(zoom) < ZOOM_THRESHOLD:
            try:
                zoom_level = float(zoom)
                # Efficient Grid Clustering
                # We use a larger grid size to aggressively merge nearby points and avoid "satellites".
                # 160 at zoom 0 is ~2/3 of world width.
                # Heuristic: 160 / 2^zoom
                grid_size = 160 / (2 ** zoom_level)
                
                # Minimum grid size
                grid_size = max(grid_size, 0.02)

                # Filter by bbox
                queryset = self.filter_queryset(self.get_queryset())

                # Aggregation
                # SnapToGrid + Centroid:
                clusters = queryset.annotate(
                    grid_point=SnapToGrid('coordinates', grid_size)
                ).values('grid_point').annotate(
                    count=Count('id'),
                    center=Centroid(Collect('coordinates'))
                )

                # Custom GeoJSON construction
                features = []
                for cluster in clusters:
                    location = cluster['center'] or cluster['grid_point']
                    
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [location.x, location.y]
                        },
                        "properties": {
                            "count": cluster['count'],
                            "is_cluster": True
                        }
                    })

                return Response({
                    "type": "FeatureCollection",
                    "features": features
                })

            except ValueError:
                pass # Fallback to normal list if zoom is invalid

        return super().list(request, *args, **kwargs)
