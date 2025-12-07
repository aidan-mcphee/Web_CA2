from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Article

class ArticleSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Article
        geo_field = "coordinates"
        fields = ('id', 'title', 'oldest_date')
