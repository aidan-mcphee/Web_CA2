from django.db import models
from django.contrib.gis.db import models as gis_models

# Create your models here.
class Article(gis_models.Model):
    title = models.CharField(max_length=200)
    oldest_date = models.DateField(null=True)
    coordinates = gis_models.PointField(srid=4326)

    def __str__(self):
        return self.title

class UserDiscovery(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    discovered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article')
        verbose_name_plural = "User Discoveries"