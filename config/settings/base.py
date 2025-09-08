from pathlib import Path
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env(DEBUG=(bool, False))
# don't call read_env here; __init__ already read it. but safe to read again if needed
# environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='unsafe-dev-secret')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1','localhost'])

# Application definition
INSTALLED_APPS = [
    # Unfold must be placed before django.contrib.admin (recommended by Unfold docs)
    'unfold',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Allauth-এর জন্য
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework.authtoken',
    'dj_rest_auth',
    'dj_rest_auth.registration',  # Social registration
    'corsheaders',
    'drf_yasg',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',  # Google প্রোভাইডার

    # Your apps
    'Authentication',
    'core',
    'ecommerce',
]

# 2. allauth Step 2
SITE_ID = 1

#3. allauth step 3
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  
    'allauth.account.auth_backends.AuthenticationBackend',  
]


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}


ACCOUNT_ADAPTER = 'Authentication.adapters.CustomAccountAdapter'
ACCOUNT_FORMS = {
      'signup': 'Authentication.forms.CustomSignupForm'
  }
ACCOUNT_SIGNUP_FIELDS = ['username*', 'email*', 'phone_number', 'password1*', 'password2*']  
ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = 'address'

ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_TIMEOUT = 180  # ৩ মিনিট
ACCOUNT_CHANGE_EMAIL = False  # একাধিক ইমেল অ্যালাউ
ACCOUNT_MAX_EMAIL_ADDRESSES = 5  
  
# 4. Allauth সেটিংস
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'  # ইউজারনেম বা ইমেল দিয়ে লগইন
ACCOUNT_EMAIL_REQUIRED = True  # সাইনআপে ইমেল বাধ্যতামূলক
ACCOUNT_EMAIL_VERIFICATION = 'none'  # ইমেল ভেরিফিকেশন বাধ্যতামূলক
ACCOUNT_SIGNUP_REDIRECT_URL = '/profile/'  # সাইনআপের পর রিডিরেক্ট
LOGIN_REDIRECT_URL = '/dashboard/'  # লগইনের পর রিডিরেক্ট
LOGOUT_REDIRECT_URL = '/'  # লগআউটের পর রিডিরেক্ট

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # should be high up
    'django.middleware.security.SecurityMiddleware',
    # optionally WhiteNoise middleware if you use it in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",

]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                 'ecommerce.context_processors.ecommerce_context',

            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database: use DATABASE_URL in env or fallback to sqlite
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# Password validation (default Django validators)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # dev static
STATIC_ROOT = BASE_DIR / 'staticfiles'    # collectstatic destination for production

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}


# CORS: default deny, override in dev/prod
CORS_ALLOWED_ORIGINS = []

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Unfold admin config will be imported from unfold_admin.py (keeps base clean)
try:
    from .unfold_admin import UNFOLD  # noqa
except ImportError:
    UNFOLD = {}
