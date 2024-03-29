"""
Django settings for youe_backend project.

Generated by 'django-admin startproject' using Django 4.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
from twilio.rest import Client
import environ
import os
from pathlib import Path

env = environ.Env()
environ.Env.read_env()
environment=env('ENV')

base_url=env('BASE_URL')
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
if environment=='LOCAL':
    ALLOWED_HOSTS = []
elif environment=='UAT':
    ALLOWED_HOSTS = ['54.208.252.254','127.0.0.1']

    CORS_ALLOWED_ORIGINS = [
            "http://localhost:3000","http://54.208.252.254","http://youe-app.albiorixtech.in","https://youe.co","https://www.youe.co"
    ]
elif environment=='PROD':
    ALLOWED_HOSTS = ['api.youe.co']
    CORS_ALLOWED_ORIGINS = [
            "https://youe.co","https://www.youe.co"
    ]
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'users',
    'core',
    'payments',
    'nodemap',
    'linkedin',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'youe_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS':  [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'youe_backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey' # Name for all the SenGrid accounts
EMAIL_HOST_PASSWORD = env('SENDGRID_API_KEY')
STRIPE_WEBHOOK_SECRET=env('STRIPE_WEBHOOK_SECRET')
STRIPE_SECRET_KEY=env('STRIPE_SECRET_KEY')
# The email you'll be sending emails from
DEFAULT_FROM_EMAIL = env('FROM_EMAIL', default='noreply@gmail.com')
OPENAI_API_KEY = env('OPENAI_API_KEY')
LINKEDIN_CLIENT_ID = env('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = env('LINKEDIN_CLIENT_SECRET')
PROXY_CURL_API_KEY=env('PROXY_CURL_API_KEY')

#for sms services
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER=env('TWILIO_NUMBER')
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

#aws credintils
# DEFAULT_FILE_STORAGE='storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_DEFAULT_REGION=env("AWS_DEFAULT_REGION")
AWS_S3_CUSTOM_DOMAIN='%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher']

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR,'media')
STATICFILES_DIRS=[
    BASE_DIR/"static",
]
# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
