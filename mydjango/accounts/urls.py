from . import views
from .views import RegisterAPI, QueryOverpass
from django.urls import path
from knox import views as knox_views
from .views import LoginAPI

urlpatterns = [
    path('api/register/', RegisterAPI.as_view(), name='register'),
    path('api/login/', LoginAPI.as_view(), name='login'),
    path('api/logout/', knox_views.LogoutView.as_view(), name='logout'),
    path('api/logoutall/', knox_views.LogoutAllView.as_view(), name='logoutall'),
    path('api/updatedb/', views.update_database, name='updatedb'),
    path('api/overpass/', QueryOverpass.as_view(), name='overpass'),
    path('api/check_auth/', views.check_auth, name='check_auth'),

]

