"""
Django settings for src project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from datetime import timedelta

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'cand2hjv-k500wm#nni_+xbsr$pza0or)rw-6!zf6ljs)i63*k'

def env_var(key, default=None):
    """Retrieves env vars and makes Python boolean replacements"""
    val = os.environ.get(key, default)
    if val == 'True':
        val = True
    elif val == 'False':
        val = False
    return val

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_var('django_debug', True)


ALLOWED_HOSTS = [
    env_var('API_BASE_HOST', 'localhost'),
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',

    'rest_framework',
    'corsheaders',
    'django_filters',
    'rest_framework_swagger',

    'src.common',
    'src.custom_auth',
    'src.incidents',
    'src.events',
    'src.reporting',
    'src.file_upload',
    'src.notifications',

    'channels',
]

AUTH_USER_MODEL = 'custom_auth.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'src.urls'

# TODO: need to use redis channel layer in prod
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'src.wsgi.application'
ASGI_APPLICATION = "src.routing.application"

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env_var('DATABASE_NAME', 'request'),
        'USER': env_var('DATABASE_USER', 'root'),
        'PASSWORD': env_var('DATABASE_PWD', 'root'),
        'HOST': env_var('DATABASE_HOST', 'localhost'),   # Or an IP Address that your DB is hosted on
        'PORT': env_var("DATABASE_PORT", '3306'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Colombo'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'


REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'src.renderer.CustomJSONRenderer',
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'EXCEPTION_HANDLER': 'src.exception_handler.custom_exception_handler',
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    )
}

JWT_AUTH = {
    'JWT_RESPONSE_PAYLOAD_HANDLER':
    'src.jwt.jwt_response_payload_handler',

    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_LEEWAY': 0,
    'JWT_EXPIRATION_DELTA': timedelta(seconds=3000),
}

# Application security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY" # used to prevent clickjacking

CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = [
    env_var('APP_BASE_URL', 'http://localhost:3000'),
]

# set seeder folder for loaddata
FIXTURE_DIRS = [
    "./seeddata/"
]

# PDF endpoint for report generation
PDF_SERVICE_ENDPOINT = env_var('PDF_SERVICE_ENDPOINT')

# Email parameters
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env_var('EMAIL_HOST')
EMAIL_PORT = env_var('EMAIL_PORT')
EMAIL_HOST_USER = env_var('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env_var('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = env_var('EMAIL_USE_TLS', False)
EMAIL_USE_SSL = env_var('EMAIL_USE_SSL', False)
EMAIL_FROM_ADDRESS = env_var('EMAIL_FROM_ADDRESS')

SMS_GATEWAY_USER=env_var('SMS_GATEWAY_USER')
SMS_GATEWAY_PASSWORD=env_var('SMS_GATEWAY_PASSWORD')
SMS_GATEWAY_BASE_URL=env_var('SMS_GATEWAY_BASE_URL')

# set frontend APP_BASE_URL for notifications sent via sms and email
APP_BASE_URL=env_var('APP_BASE_URL', 'http://localhost:3000')
