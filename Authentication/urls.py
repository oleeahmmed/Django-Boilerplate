from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import RegisterView, CustomLoginView

router = DefaultRouter()

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
]

urlpatterns += router.urls
