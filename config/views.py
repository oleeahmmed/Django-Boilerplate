from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return HttpResponse("Car Dealing System - Welcome!")


from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = 'http://localhost:8000/accounts/google/login/callback/'  # Google Console-এ ম্যাচ করুন
    client_class = OAuth2Client