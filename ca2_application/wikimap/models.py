from django.db import models
from django.contrib.gis.db import models as gis_models

# Create your models here.
class Article(gis_models.Model):
    title = models.CharField(max_length=200)
    oldest_date = models.DateField(null=True)
    coordinates = gis_models.PointField(srid=4326)