# Cloud extra settings
import os
import boto3

print('In Cloud Settings')

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            'bucket_name': os.environ['BUCKET_NAME'],
            'location': 'media/',
            'access_key': os.environ['AWS_ACCESS_KEY_ID'],
            'secret_key': os.environ['AWS_SECRET_ACCESS_KEY'],
            'security_token': os.environ['AWS_SESSION_TOKEN'],
            'region_name': os.environ.get('AWS_REGION_NAME', None),
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
DEBUG = False

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = ['https://' +
                        os.environ['CLOUDFRONT_DISTRIBUTION_DOMAINNAME']]


WHITENOISE_MAX_AGE = 60*60*24

STATIC_HOST = "https://" + \
    os.environ['CLOUDFRONT_DISTRIBUTION_DOMAINNAME'] if not DEBUG else ""
STATIC_URL = STATIC_HOST + "/static/"

WAGTAILADMIN_BASE_URL = 'https://' + \
    os.environ['CLOUDFRONT_DISTRIBUTION_DOMAINNAME']

WAGTAILFRONTENDCACHE = {
    'cloudfront': {
        'BACKEND': 'wagtail.contrib.frontend_cache.backends.CloudfrontBackend',
        'DISTRIBUTION_ID': os.environ['CLOUDFRONT_DISTRIBUTION_ID'],
    },
}
ROOT_URLCONF = 'mysite.urls'


MEDIA_URL = 'https://' + \
    os.environ['CLOUDFRONT_DISTRIBUTION_DOMAINNAME']+'/media/'


MEDIA_ROOT = None
