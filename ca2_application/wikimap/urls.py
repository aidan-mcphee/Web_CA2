from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet, basename='article')

urlpatterns = [
    path('', views.index, name='index'),
    path('map/', views.map_view, name='map'),
    path('api/summary/<str:title>/', views.article_summary, name='article_summary'),
    path('api/search/', views.search_articles, name='search_articles'),
    path('api/', include(router.urls)),
]
