"""
RAKSHAK-AI — Custom Permission Classes

Roles:
  admin        → sees / manages ALL companies' data
  company_user → sees / manages ONLY their own company's data
  viewer       → read-only, scoped to their company
"""
from rest_framework.permissions import BasePermission, IsAuthenticated


def _get_profile(user):
    try:
        return user.company_profile   # reverse of CompanyUser.user OneToOne
    except Exception:
        return None


class IsAdminRole(BasePermission):
    """Allow only users with role='admin'."""
    message = "You must be a RAKSHAK admin to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = _get_profile(request.user)
        return profile is not None and profile.role == 'admin'


class IsCompanyUserOrAdmin(BasePermission):
    """Any authenticated company_user or admin. Write blocked for viewers."""
    message = "Authentication required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = _get_profile(request.user)
        if profile is None:
            return False
        # Viewers get read-only
        if profile.role == 'viewer' and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            self.message = "Viewers have read-only access."
            return False
        return True


def get_company_filter(user):
    """
    Returns a dict to use as queryset filter kwargs.
    admin → {} (no filter = all data)
    company_user / viewer → {'company': <company>} or relevant variant
    """
    profile = _get_profile(user)
    if profile is None or profile.role == 'admin':
        return None   # caller should NOT filter
    return profile.company
