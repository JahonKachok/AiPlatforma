from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("login/2fa/", views.TwoFactorChallengeView.as_view(), name="2fa_challenge"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("profile/2fa/setup/", views.two_factor_setup, name="2fa_setup"),
    path("profile/2fa/disable/", views.two_factor_disable, name="2fa_disable"),
    path("profile/login-journal/", views.login_journal, name="login_journal"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<uuid:pk>/edit/", views.user_update, name="user_update"),
]
