from django.db import models

class ProductionEntry(models.Model):
    item_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    date = models.DateField(auto_now_add=True)
