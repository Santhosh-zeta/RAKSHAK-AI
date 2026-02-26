"""
RAKSHAK-AI — Auth Endpoints

POST /api/auth/login/           → token + profile
POST /api/auth/logout/          → delete token
GET  /api/auth/me/              → current user + company
POST /api/auth/change-password/ → update own password
POST /api/auth/register/        → admin creates a company user  [Admin only]
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import LogisticsCompany, CompanyUser
from .serializers import CompanyUserSerializer, LogisticsCompanySerializer
from .permissions import IsAdminRole


class LoginView(views.APIView):
    """
    POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    Returns: { "token": "...", "user": {...}, "company": {...} | null }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {"error": "username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if not user.is_active:
            return Response(
                {"error": "Account is deactivated. Contact your admin."},
                status=status.HTTP_403_FORBIDDEN
            )

        token, _ = Token.objects.get_or_create(user=user)

        try:
            profile = user.company_profile
            company_data = LogisticsCompanySerializer(profile.company).data if profile.company else None
        except Exception:
            return Response(
                {"error": "User has no RAKSHAK profile. Contact admin."},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            "token": token.key,
            "user": CompanyUserSerializer(profile).data,
            "company": company_data,
        }, status=status.HTTP_200_OK)


class LogoutView(views.APIView):
    """DELETE /api/auth/logout/ — invalidate the current token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.auth.delete()
        except Exception:
            pass
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class MeView(views.APIView):
    """GET /api/auth/me/ — return the current user's profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.company_profile
        except Exception:
            return Response({"error": "No profile found."}, status=status.HTTP_404_NOT_FOUND)

        company_data = LogisticsCompanySerializer(profile.company).data if profile.company else None
        return Response({
            "user": CompanyUserSerializer(profile).data,
            "company": company_data,
        })

    def patch(self, request):
        """Update own first/last name and email."""
        user = request.user
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name  = request.data.get('last_name',  user.last_name)
        user.email      = request.data.get('email',      user.email)
        user.save()
        return Response({"message": "Profile updated."})


class ChangePasswordView(views.APIView):
    """
    POST /api/auth/change-password/
    Body: { "old_password": "...", "new_password": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_pw = request.data.get('old_password', '')
        new_pw = request.data.get('new_password', '')

        if not old_pw or not new_pw:
            return Response(
                {"error": "old_password and new_password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(new_pw) < 8:
            return Response(
                {"error": "New password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not request.user.check_password(old_pw):
            return Response(
                {"error": "Old password is incorrect."},
                status=status.HTTP_403_FORBIDDEN
            )

        request.user.set_password(new_pw)
        request.user.save()
        # Refresh token after password change
        Token.objects.filter(user=request.user).delete()
        new_token = Token.objects.create(user=request.user)
        return Response({
            "message": "Password changed successfully.",
            "new_token": new_token.key,
        }, status=status.HTTP_200_OK)


class RegisterView(views.APIView):
    """
    POST /api/auth/register/          [Admin only]
    Creates a Django User + CompanyUser profile.
    Body: {
        "username": "company1_admin",
        "password": "SecurePass123",
        "email": "ops@company.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "company_user",        // admin | company_user | viewer
        "company_id": "<uuid>"         // required unless role=admin
    }
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        username   = request.data.get('username', '').strip()
        password   = request.data.get('password', '')
        email      = request.data.get('email', '').strip()
        first_name = request.data.get('first_name', '').strip()
        last_name  = request.data.get('last_name', '').strip()
        role       = request.data.get('role', 'company_user')
        company_id = request.data.get('company_id')

        # Validate
        if not username or not password:
            return Response(
                {"error": "username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": f"Username '{username}' already taken."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if role not in ('admin', 'company_user', 'viewer'):
            return Response(
                {"error": "role must be one of: admin, company_user, viewer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = None
        if role != 'admin':
            if not company_id:
                return Response(
                    {"error": "company_id is required for non-admin users."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                company = LogisticsCompany.objects.get(company_id=company_id)
            except LogisticsCompany.DoesNotExist:
                return Response(
                    {"error": "Company not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Create Django user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        # Create CompanyUser profile
        profile = CompanyUser.objects.create(
            user=user,
            company=company,
            role=role,
        )

        token = Token.objects.create(user=user)

        return Response({
            "message": f"User '{username}' created successfully.",
            "user": CompanyUserSerializer(profile).data,
            "token": token.key,
        }, status=status.HTTP_201_CREATED)


class CompanyRegistrationView(views.APIView):
    """
    POST /api/auth/register-company/  [Public]
    Allows a brand new company to sign up themselves.
    Creates the LogisticsCompany + initial admin User + CompanyUser profile.
    Body: {
        "company_name": "New Logistics Corp",
        "company_city": "Mumbai",
        "username": "new_corp_admin",
        "password": "SecurePass123",
        "email": "admin@newcorp.com",
        "first_name": "Jane",
        "last_name": "Doe"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        company_name = request.data.get('company_name', '').strip()
        company_city = request.data.get('company_city', '').strip()
        username     = request.data.get('username', '').strip()
        password     = request.data.get('password', '')
        email        = request.data.get('email', '').strip()
        first_name   = request.data.get('first_name', '').strip()
        last_name    = request.data.get('last_name', '').strip()

        # Validate
        if not company_name:
            return Response({"error": "company_name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not username or not password:
            return Response({"error": "username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"error": f"Username '{username}' already taken."}, status=status.HTTP_400_BAD_REQUEST)
        if LogisticsCompany.objects.filter(name__iexact=company_name).exists():
            return Response({"error": f"Company '{company_name}' already registered."}, status=status.HTTP_400_BAD_REQUEST)

        # Create Company
        company = LogisticsCompany.objects.create(
            name=company_name,
            city=company_city,
            control_email=email
        )

        # Create User
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        # Create Profile
        profile = CompanyUser.objects.create(
            user=user,
            company=company,
            role='company_user'  # the first user is basically the company admin
        )

        # Auth Token
        token = Token.objects.create(user=user)

        return Response({
            "message": "Company registered successfully.",
            "token": token.key,
            "user": CompanyUserSerializer(profile).data,
            "company": LogisticsCompanySerializer(company).data
        }, status=status.HTTP_201_CREATED)

