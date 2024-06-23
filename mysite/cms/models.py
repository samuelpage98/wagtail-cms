# models.py
from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail import blocks
from wagtail.images.models import Image
from .blocks import HeaderBlock

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


class HeaderPage(Page):
    body = StreamField(HeaderBlock(), blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]
