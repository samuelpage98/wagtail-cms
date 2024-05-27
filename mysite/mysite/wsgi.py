"""
WSGI config for mysite project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""
from __future__ import annotations
from django.core.wsgi import get_wsgi_application
from apig_wsgi import make_lambda_handler
from apig_wsgi.compat import WSGIApplication
from typing import cast
from typing import Any
import json
import os
import logging
logger = logging.getLogger()
logger.setLevel("DEBUG")


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')


application = cast(  # incomplete hints in django-stubs
    WSGIApplication, get_wsgi_application()
)

apig_wsgi_handler = make_lambda_handler(
    application, binary_support=None)

# non_binary_content_type_prefixes=['image/svg+xml', 'text', 'application/json']


def lambda_handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    # logger.info(event['requestContext']['path'])
    logger.info(json.dumps(event, indent=2, sort_keys=True))
    response = apig_wsgi_handler(event, context)
    logger.info(json.dumps(response, indent=2, sort_keys=True))
    return response
