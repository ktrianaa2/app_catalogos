from rest_framework.routers import DefaultRouter
from .views import ImagenViewSet
router = DefaultRouter()
router.register(r'imagenes', ImagenViewSet)
urlpatterns = router.urls
