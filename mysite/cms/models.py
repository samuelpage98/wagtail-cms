from django.db import models
from django.views.generic.base import TemplateResponseMixin, ContextMixin

from modelcluster.fields import ParentalKey
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.search import index
from wagtail.contrib.forms.models import AbstractForm, AbstractFormField
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit
from crispy_forms_gds.layout import Field


class FormField(AbstractFormField):
    page = ParentalKey('FormPage', on_delete=models.CASCADE,
                       related_name='form_fields')


class FormPage(AbstractForm):
    content_panels = AbstractForm.content_panels + [
        InlinePanel('form_fields', label="Form fields"),
        FormSubmissionsPanel(),
    ]


class Topic(models.Model):
    """A topic the user is learning about."""
    text = models.CharField(max_length=200)
    other_text = models.CharField(max_length=200)
    date_added = models.DateTimeField(
        auto_now_add=True)

    def __str__(self):
        return self.text


class Entry(models.Model):
    """Learning log entries for a topic."""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    text = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:50]}..."
