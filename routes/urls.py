from django.urls import path
from . import views

urlpatterns = [
    # Trip endpoints
    path('trips/', views.TripAPIView.as_view(), name='trip-list'),
    path('trips/<uuid:id>/', views.TripDetailAPIView.as_view(), name='trip-detail'),
    
    # Daily logs
    path('trips/<uuid:trip_id>/days/<int:day_number>/logs/', views.DailyLogsAPIView.as_view(), 
         name='daily-logs'),
    
    # Legacy endpoints (kept for backward compatibility)
    path('route/', views.LegacyRouteAPIView.as_view(), name='legacy-route'),
    path('logs/', views.LegacyLogsAPIView.as_view(), name='legacy-logs'),
]
