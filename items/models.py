from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()
    stock_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
