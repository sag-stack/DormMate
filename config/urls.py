from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView # <-- Import this

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Send any URL starting with 'api/' to your 'dorm' app's urls.py
    path('api/', include('dorm.urls')), 
    
    # --- ADD THIS LINE ---
    # Redirect the root URL "/" to your login page
    path('', RedirectView.as_view(url='/api/login/', permanent=True)),
]