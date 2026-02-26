from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TruckViewSet, TripViewSet, GPSLogViewSet, AlertViewSet
from .agent_views import VisionEventView, FusionRiskView, SimulationView

router = DefaultRouter()
router.register(r'trucks', TruckViewSet)
router.register(r'trips', TripViewSet)
router.register(r'gps-logs', GPSLogViewSet)
router.register(r'alerts', AlertViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('agents/vision-event/', VisionEventView.as_view(), name='vision_event'),
    path('agents/fusion-risk/', FusionRiskView.as_view(), name='fusion_risk'),
    path('agents/simulate/', SimulationView.as_view(), name='simulate'),
]
