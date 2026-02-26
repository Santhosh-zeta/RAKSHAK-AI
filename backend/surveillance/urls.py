from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TruckViewSet, TripViewSet, GPSLogViewSet, AlertViewSet
from .agent_views import (
    VisionEventView, FusionRiskView, SimulationView,
    BehaviourAnalysisView, DecisionView, PerceptionView,
    DigitalTwinView, RouteView, RiskFusionView, ExplainabilityView
)

router = DefaultRouter()
router.register(r'trucks', TruckViewSet)
router.register(r'trips', TripViewSet)
router.register(r'gps-logs', GPSLogViewSet)
router.register(r'alerts', AlertViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('agents/vision-event/',        VisionEventView.as_view(),        name='vision_event'),
    path('agents/fusion-risk/',         FusionRiskView.as_view(),         name='fusion_risk'),
    path('agents/simulate/',            SimulationView.as_view(),         name='simulate'),
    path('agents/behaviour-analysis/',  BehaviourAnalysisView.as_view(),  name='behaviour_analysis'),
    path('agents/decision/',            DecisionView.as_view(),            name='decision'),
    path('agents/perception/',          PerceptionView.as_view(),          name='perception'),
    path('agents/digital-twin/',        DigitalTwinView.as_view(),        name='digital_twin'),
    path('agents/route/',               RouteView.as_view(),               name='route'),
    path('agents/risk-fusion/',         RiskFusionView.as_view(),         name='risk_fusion'),
    path('agents/explain/',             ExplainabilityView.as_view(),     name='explain'),
]

