from django.urls import path
from . import views
from .views import PredictionCreateView, LocationCreateView, DeviceIPUpsertView, DeviceStatusView, device_page, map_page, history_page, profile, deactivate_account,delete_account, activate, login_view, deactivate_account , delete_account, logout_view


urlpatterns = [
    path('predictions/', PredictionCreateView.as_view(), name='create_prediction'),
    path('locations/', LocationCreateView.as_view(), name='create_location'),
    path('device_ip/', DeviceIPUpsertView.as_view(), name='upsert_device_ip'),
    path('device_status/', DeviceStatusView.as_view(), name='device_status'),
    path('devices/', device_page, name='device_page'),
    path('api/get_last_location/<str:device_id>/', views.get_last_location, name='get_last_location'),
    path('map/', map_page, name='map_page'),
    path('api/predictions/<str:device_id>/', views.device_predictions, name='device_predictions'),
    path('api/locations/<str:device_id>/', views.device_locations, name='device_locations'),
    path('api/all_predictions/', views.all_predictions, name='all_predictions'),
    path('history/', history_page, name='history_page'),
    path('profile/', profile, name='profile'),
    path('profile/deactivate/', deactivate_account, name='deactivate_account'),
    path('profile/delete/', delete_account, name='delete_account'),
    path('register/', views.register, name='register'),
    path('login/', login_view, name='login'),
    path('activate/<uidb64>/<token>/', activate, name='activate'),
    path('deactivate/', deactivate_account, name='deactivate_account'),
    path('delete/', delete_account, name='delete_account'),
    path('logout/', logout_view, name='logout'),

]


    



    

