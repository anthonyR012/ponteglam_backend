from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import MixinAudit


class HeadquarterRating(MixinAudit):

    headquarter = models.ForeignKey(
        'headquarters.Headquarter', on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter_rating'
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter_rating'
    )
    rating = models.IntegerField(
        validators=[
            MaxValueValidator(5),
            MinValueValidator(1)
        ]
    )

    def __str__(self):
        return f'HQ: {self.headquarter} - Rating: {self.rating}'


class HeadquarterServiceRating(MixinAudit):

    headquarter_service = models.ForeignKey(
        'headquarters.HeadquarterService', on_delete=models.CASCADE,
        related_name='headquarter_service_rating'
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, null=True, blank=True,
        related_name='headquarter_service_rating'
    )
    rating = models.IntegerField(
        validators=[
            MaxValueValidator(5),
            MinValueValidator(1)
        ]
    )
    comment = models.TextField()
    supplier_reply = models.TextField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.comment
