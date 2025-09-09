from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django import forms

def home(request):
    return HttpResponse("Car Dealing System - Welcome!")

from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = 'http://localhost:8000/accounts/google/login/callback/'
    client_class = OAuth2Client

class ProfileForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    bio = forms.CharField(widget=forms.Textarea, required=False)

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'account/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['form'] = ProfileForm(initial={
            'username': self.request.user.username,
            'bio': getattr(self.request.user, 'bio', ''),
        })
        return context

    def post(self, request, *args, **kwargs):
        form = ProfileForm(request.POST)
        if form.is_valid():
            user = request.user
            user.username = form.cleaned_data['username']
            user.bio = form.cleaned_data['bio']
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return self.get(request, *args, **kwargs)
        else:
            messages.error(request, 'Failed to update profile. Please check the form.')
            return self.render_to_response(self.get_context_data(form=form))