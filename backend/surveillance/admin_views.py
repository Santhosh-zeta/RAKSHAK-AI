"""
RAKSHAK-AI — Admin Panel Endpoints  [Admin role required]

GET    /api/admin/dashboard/        → platform-wide stats
GET    /api/admin/companies/        → all companies + stats
GET    /api/admin/users/            → all CompanyUsers
POST   /api/admin/users/            → create user (same as /api/auth/register/)
GET    /api/admin/users/<id>/       → user detail
PUT    /api/admin/users/<id>/       → update user (role / company / active)
DELETE /api/admin/users/<id>/       → deactivate user
GET    /api/admin/alerts/           → all alerts platform-wide (with filters)
"""
from rest_framework import views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db.models import Count, Q

from .models import LogisticsCompany, CompanyUser, Truck, Trip, Alert
from .serializers import (
    LogisticsCompanySerializer, CompanyUserSerializer,
    AlertSerializer, TruckSerializer, TripSerializer,
)
from .permissions import IsAdminRole


class AdminDashboardView(views.APIView):
    """GET /api/admin/dashboard/ — platform-wide KPIs."""
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        companies  = LogisticsCompany.objects.count()
        trucks     = Truck.objects.count()
        active_trips = Trip.objects.filter(status__in=['Scheduled', 'In-Transit']).count()
        alert_trips  = Trip.objects.filter(status='Alert').count()
        total_alerts    = Alert.objects.count()
        critical_alerts = Alert.objects.filter(severity='Critical', resolved=False).count()
        unresolved      = Alert.objects.filter(resolved=False).count()
        users = CompanyUser.objects.count()

        return Response({
            "platform_stats": {
                "total_companies":    companies,
                "total_trucks":       trucks,
                "total_users":        users,
                "active_trips":       active_trips,
                "alert_trips":        alert_trips,
                "total_alerts":       total_alerts,
                "unresolved_alerts":  unresolved,
                "critical_alerts":    critical_alerts,
            },
            "companies_snapshot": [
                {
                    "name":    c.name,
                    "city":    c.city,
                    "id":      c.company_id,
                    "trucks":  c.trucks.count(),
                    "active_trips": Trip.objects.filter(
                        truck__company=c,
                        status__in=['Scheduled', 'In-Transit']
                    ).count(),
                    "open_alerts": Alert.objects.filter(
                        trip__truck__company=c, resolved=False
                    ).count(),
                }
                for c in LogisticsCompany.objects.all()[:10]
            ]
        })


class AdminCompanyListView(views.APIView):
    """GET /api/admin/companies/ — all companies with full stats."""
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        companies = LogisticsCompany.objects.prefetch_related('contacts', 'trucks').all()
        data = []
        for c in companies:
            trucks = c.trucks.all()
            truck_ids = trucks.values_list('truck_id', flat=True)
            trips  = Trip.objects.filter(truck__truck_id__in=truck_ids)
            data.append({
                **LogisticsCompanySerializer(c).data,
                "stats": {
                    "trucks":       trucks.count(),
                    "active_trucks": trucks.filter(active=True).count(),
                    "total_trips":   trips.count(),
                    "alert_trips":   trips.filter(status='Alert').count(),
                    "active_trips":  trips.filter(status__in=['Scheduled', 'In-Transit']).count(),
                    "open_alerts":   Alert.objects.filter(trip__in=trips, resolved=False).count(),
                    "users": CompanyUser.objects.filter(company=c).count(),
                }
            })
        return Response(data)


class AdminUserListView(views.APIView):
    """
    GET  /api/admin/users/   → list all CompanyUsers
    POST /api/admin/users/   → create a new CompanyUser
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        qs = CompanyUser.objects.select_related('user', 'company').all()
        company_id = request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(company__company_id=company_id)
        role = request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return Response(CompanyUserSerializer(qs, many=True).data)

    def post(self, request):
        """Delegates to RegisterView logic."""
        from .auth_views import RegisterView
        return RegisterView.as_view()(request._request)


class AdminUserDetailView(views.APIView):
    """
    GET    /api/admin/users/<id>/
    PUT    /api/admin/users/<id>/  → update role / company / active status
    DELETE /api/admin/users/<id>/  → deactivate (not hard delete)
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def _get_profile(self, pk):
        try:
            return CompanyUser.objects.select_related('user', 'company').get(pk=pk)
        except CompanyUser.DoesNotExist:
            return None

    def get(self, request, pk):
        profile = self._get_profile(pk)
        if not profile:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CompanyUserSerializer(profile).data)

    def put(self, request, pk):
        profile = self._get_profile(pk)
        if not profile:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Update role
        new_role = request.data.get('role')
        if new_role and new_role in ('admin', 'company_user', 'viewer'):
            profile.role = new_role

        # Update company assignment
        company_id = request.data.get('company_id')
        if company_id:
            try:
                profile.company = LogisticsCompany.objects.get(company_id=company_id)
            except LogisticsCompany.DoesNotExist:
                return Response({"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        # Update active state
        if 'is_active' in request.data:
            profile.is_active = bool(request.data['is_active'])
            profile.user.is_active = profile.is_active
            profile.user.save()

        # Update name / email on the Django User
        user = profile.user
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name  = request.data.get('last_name',  user.last_name)
        user.email      = request.data.get('email',      user.email)
        user.save()

        profile.save()
        return Response({
            "message": "User updated.",
            "user": CompanyUserSerializer(profile).data,
        })

    def delete(self, request, pk):
        profile = self._get_profile(pk)
        if not profile:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Soft-delete: deactivate instead of hard delete
        profile.is_active = False
        profile.save()
        profile.user.is_active = False
        profile.user.save()
        return Response({"message": f"User '{profile.user.username}' deactivated."})


class AdminAlertListView(views.APIView):
    """
    GET /api/admin/alerts/
    Query params: company_id, severity, resolved, type
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        qs = Alert.objects.select_related(
            'trip__truck__company'
        ).all().order_by('-timestamp')

        company_id = request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(trip__truck__company__company_id=company_id)

        severity = request.query_params.get('severity')
        if severity:
            qs = qs.filter(severity=severity)

        resolved = request.query_params.get('resolved')
        if resolved is not None:
            qs = qs.filter(resolved=resolved.lower() == 'true')

        alert_type = request.query_params.get('type')
        if alert_type:
            qs = qs.filter(type=alert_type)

        return Response(AlertSerializer(qs[:100], many=True).data)
