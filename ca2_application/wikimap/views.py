from django.shortcuts import render
from rest_framework import viewsets
from rest_framework_gis.filters import InBBoxFilter
from .models import Article
from .serializers import ArticleSerializer
from django.contrib.gis.db.models.functions import SnapToGrid, Centroid
from django.contrib.gis.db.models.aggregates import Collect
from django.db.models import Count
from rest_framework.response import Response

# Page views
def index(request):
    return render(request, 'wikimap/index.html')

def map_view(request):
    return render(request, 'wikimap/map.html')


# API Views
class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    bbox_filter_field = 'coordinates' 
    filter_backends = (InBBoxFilter,)
    pagination_class = None

    def list(self, request, *args, **kwargs):
        zoom = request.query_params.get('zoom')
        if zoom and float(zoom) < 14:
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
