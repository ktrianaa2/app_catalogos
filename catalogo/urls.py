from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ImagenViewSet, index, classify_local

router = DefaultRouter()
router.register(r'imagenes', ImagenViewSet)

urlpatterns = [
    path('', index, name='index'),         # frontend en /
    path('classify/', classify_local),     # → /api/classify/
] + router.urls