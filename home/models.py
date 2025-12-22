from django.db import models

from wagtail.models import Page


class HomePage(Page):
    title_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="this is a test only"
    )
