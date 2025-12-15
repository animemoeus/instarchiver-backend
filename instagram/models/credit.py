from django.db import models
from simple_history.models import HistoricalRecords

from payments.models import Payment

from .user import User


class StoryCredit(models.Model):
    user = models.OneToOneField("instagram.User", on_delete=models.CASCADE)
    credit = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Story Credit"
        verbose_name_plural = "Story Credits"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Story Credit for {self.user.username}"


class StoryCreditPayment(models.Model):
    story_credit = models.ForeignKey(StoryCredit, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

    credit = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Story Credit Payment"
        verbose_name_plural = "Story Credit Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Story Credit Payment for {self.story_credit.user.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_story_credit()

    def update_story_credit(self):
        self.story_credit.credit += self.credit
        self.story_credit.save()

    @staticmethod
    def create_record(payment_id, instagram_user_id, credit):
        instagram_user = User.objects.get(uuid=instagram_user_id)
        story_credit, _ = StoryCredit.objects.get_or_create(user=instagram_user)
        payment = Payment.objects.get(id=payment_id)

        return StoryCreditPayment.objects.create(
            story_credit=story_credit,
            payment=payment,
            credit=credit,
        )
