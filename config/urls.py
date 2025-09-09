from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import GoogleLogin, ProfileView

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
   openapi.Info(
      title="Your API Title",
      default_version='v1',
      description="API description",
      terms_of_service="https://www.yourcompany.com/terms/",
      contact=openapi.Contact(email="contact@yourcompany.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('Authentication.urls')),
    path('accounts/', include('allauth.urls')),  # Allauth
    path('dj-rest-auth/', include('dj_rest_auth.urls')),  # REST auth
    path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),  # Social registration
    path('api/', include('Authentication.urls')),

    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Debug Toolbar only in development mode
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)