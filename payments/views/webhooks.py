from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import WebhookLog


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        webhook_log = WebhookLog(
            reference_type=WebhookLog.REFERENCE_STRIPE,
            reference=request.data.get("id"),
            raw_data=request.data,
        )
        webhook_log.save()

        return Response({"status": "ok"})
