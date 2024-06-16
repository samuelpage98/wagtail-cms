import mimetypes
from pathlib import Path
import os


mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-6kk)r$tlbt#8g@9*=z#)ybh&85jdn+5gp=#*91o8*$$d=c192a'
DEBUG = True

ALLOWED_HOSTS = ['*']


CSRF_TRUSTED_ORIGINS = ['http://localhost']

WHITENOISE_MAX_AGE = 60*60*24

STATIC_URL = "/static/"
INSTALLED_APPS = [

    'jazzmin',
    'yapp',
    'cms',
    'nested_admin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django_s3_sqlite",
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',
    'wagtail.contrib.frontend_cache',
    'modelcluster',
    'taggit',
    'storages',
    'crispy_forms',
    'crispy_forms_gds',
    'wagtail.contrib.settings',
]


CRISPY_ALLOWED_TEMPLATE_PACKS = "gds"
CRISPY_TEMPLATE_PACK = "gds"


WAGTAIL_SITE_NAME = 'John Tech'
WAGTAILDOCS_EXTENSIONS = ['csv', 'docx', 'key',
                          'odt', 'pdf', 'pptx', 'rtf', 'txt', 'xlsx', 'zip']
WAGTAILADMIN_BASE_URL = 'https://localhost'


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',

]

ROOT_URLCONF = 'mysite.urls'

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

WSGI_APPLICATION = 'mysite.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('SQLITE_DB_PATH', os.path.join(BASE_DIR, 'db.sqlite3')),
    }
}

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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

MEDIA_URL = 'https://localhost/media/'
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), '..')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_ROOT = BASE_DIR / "staticfiles"

if os.getenv('LAMBDA_TASK_ROOT'):
    print('Configuring for cloud')
    try:
        from .cloud_settings import *
    except ImportError as e:
        pass
