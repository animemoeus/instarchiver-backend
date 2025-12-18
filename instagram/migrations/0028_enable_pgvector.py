# Generated manually for pgvector extension

from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    dependencies = [
        ('instagram', '0027_historicalpost_caption_post_caption'),
    ]

    operations = [
        VectorExtension()
    ]
