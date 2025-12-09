from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet, basename='article')

urlpatterns = [
    path('', views.index, name='index'),
    path('accounts/signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('map/', views.map_view, name='map'),
    path('api/summary/<path:title>/', views.article_summary, name='article_summary'),
    path('api/search/', views.search_articles, name='search_articles'),
    path('api/collect/', views.collect_article, name='collect_article'),
    path('api/', include(router.urls)),
]
