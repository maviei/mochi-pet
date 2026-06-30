from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PetViewSet, PetEventViewSet

router = DefaultRouter()
router.register("pets", PetViewSet, basename="pet")
router.register("events", PetEventViewSet, basename="event")

urlpatterns = [path("", include(router.urls))]
