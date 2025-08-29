from django.db import models
from rest_framework import status as drf_status


class APIRequestLog(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_TIMEOUT = "timeout"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
        (STATUS_TIMEOUT, "Timeout"),
    ]

    method = models.CharField(max_length=10)
    url = models.URLField(max_length=500)
    request_headers = models.JSONField(default=dict, blank=True)
    request_params = models.JSONField(default=dict, blank=True)
    request_body = models.JSONField(default=dict, blank=True)

    response_status_code = models.IntegerField(null=True, blank=True)
    response_headers = models.JSONField(default=dict, blank=True)
    response_body = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    duration_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API Request Log"
        verbose_name_plural = "API Request Logs"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["response_status_code"]),
        ]

    def __str__(self):
        endpoint = self.url.split("/")[-1] if self.url else "unknown"
        return f"{self.method} {endpoint} - {self.status}"

    @property
    def is_successful(self):
        return (
            self.status == self.STATUS_SUCCESS
            and drf_status.HTTP_200_OK
            <= (self.response_status_code or 0)
            < drf_status.HTTP_300_MULTIPLE_CHOICES
        )

    @property
    def duration_seconds(self):
        return self.duration_ms / 1000 if self.duration_ms else None
