from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('docs/<uuid:pk>/', views.detail, name='detail'),
    path('docs/<uuid:pk>/json/', views.download_json, name='download_json'),
]
