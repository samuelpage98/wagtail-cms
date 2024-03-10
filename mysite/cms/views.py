from django.shortcuts import render

# Create your views here.
from .models import Topic


def index(request):
    """The home page for Learning Log."""
    topics = Topic.objects.all()

    context = {'topics': topics,

               }

    return render(request,
                  'cms/index.html', context)
