from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail import blocks
from wagtail.images.models import Image
from .blocks import HeaderBlock
import boto3
import os
import time
import json

class RecipePage(Page):
    introduction = RichTextField(blank=True)
    ingredients = RichTextField(blank=True, help_text="Enter ingredients, separated by new lines.")
    instructions = RichTextField(blank=True)
    image = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name='+'
    )

    content_panels = Page.content_panels + [
        FieldPanel('introduction'),
        FieldPanel('ingredients'),
        FieldPanel('instructions'),
        FieldPanel('image'),
    ]

class HomePage(Page):
    introduction = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('introduction'),
    ]

    def get_context(self, request):
        context = super().get_context(request)
        context['recipes'] = RecipePage.objects.child_of(self).live().order_by('-first_published_at')
        return context

class ShoppingListPage(Page):
    content_panels = Page.content_panels

    def get_context(self, request):
        context = super().get_context(request)
        recipes = RecipePage.objects.live().order_by('title')
        context['recipes'] = recipes
        context['recipes_json'] = json.dumps([
            {
                'id': recipe.id,
                'title': recipe.title,
                'ingredients': recipe.ingredients,
            }
            for recipe in recipes
        ])
        return context

class HeaderPage(Page):
    body = StreamField(HeaderBlock(), blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


from wagtail.signals import page_published

def invalidate_cloudfront_cache(paths):
    client = boto3.client('cloudfront')

    print('Called CF cache invalidation')
    
    response = client.create_invalidation(
        DistributionId=os.environ['CLOUDFRONT_DISTRIBUTION_ID'],
        InvalidationBatch={
            'Paths': {
                'Quantity': len(paths),
                'Items': paths
            },
            'CallerReference': str(time.time()).replace(".", "")
        }
    )
    return response

def get_related_pages():
    related_pages = set()
    
    for page in HomePage.objects.live():
        related_pages.add(page.url)
    for page in ShoppingListPage.objects.live():
        related_pages.add(page.url)

    return list(related_pages)

def invalidate_cache_on_publish(sender, **kwargs):
    paths = get_related_pages()
    invalidate_cloudfront_cache(paths)

# Register listeners to invalidate cache for Home Page when Recipe Page is updated.
page_published.connect(invalidate_cache_on_publish, sender=RecipePage)
