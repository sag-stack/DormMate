from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Core App Pages
    path('home/', views.home_view, name='home'),
    path('chores/', views.chores_view, name='chores'),
    path('expenses/', views.expenses_view, name='expenses'),
    path('expenses/settle/<int:pk>/', views.settle_expense_view, name='settle_expense'),
    path('grocery/', views.grocery_view, name='grocery'),
    path('guests/', views.guests_view, name='guests'),
    path('guests/edit/<int:pk>/', views.edit_guest_view, name='edit_guest'),
    path('announcements/', views.announcements_view, name="announcements"),
    path('announcements/edit/<int:pk>/', views.edit_announcement_view, name='edit_announcement'),
    path('announcements/delete/<int:pk>/', views.delete_announcement_view, name='delete_announcement'),
    path('household/', views.household_management_view, name='household_management'),
    path('settings/', views.settings_view, name='settings'),
    path('leave-household/', views.leave_household_view, name='leave_household'),
    path('settings/delete-account/', views.delete_account_view, name='delete_account'),
    path('settings/password-change/', auth_views.PasswordChangeView.as_view(
        template_name='dorm/password_change.html',
        success_url='/api/settings/' # Go back to settings
    ), name='password_change'),
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]