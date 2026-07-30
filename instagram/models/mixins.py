from django.db import models


class InstagramModerationMixin(models.Model):
    """
    Mixin to add moderation fields to a model.
    """

    is_flagged = models.BooleanField(default=False)
    moderation_result = models.JSONField(null=True, blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"Flagged: {self.is_flagged}, Moderated At: {self.moderated_at}"

    def moderate_content(self):
        msg = "Subclasses must implement the moderate_content method."
        raise NotImplementedError(msg)


class ViewCountMixin(models.Model):
    """
    Mixin to add a per-object view counter.

    Internal analytics only, never exposed via API serializers. Must only be
    incremented via a queryset .update() call (e.g. from a Celery task), never
    via instance.save(), to avoid triggering post_save signals such as
    django-simple-history's change tracking on every view.
    """

    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
