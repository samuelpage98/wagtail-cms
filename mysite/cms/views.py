from django.shortcuts import render
from wagtail.models import Page
from .models import RecipePage

# Create your views here.
# from .models import Topic

def index(request):
    """The home page for Learning Log."""
    # topics = Topic.objects.all()

    # context = {'topics': topics,

    #            }

    response = render(request, 'cms/index.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
