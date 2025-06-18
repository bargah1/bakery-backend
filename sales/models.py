from django.db import models

class Sale(models.Model):
    quantity = models.PositiveIntegerField()
    total_price = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
