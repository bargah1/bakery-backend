from django.db import models
from items.models import Item

class CustomerVisit(models.Model):
    visit_time = models.DateTimeField(auto_now_add=True)
    items_bought = models.ManyToManyField(Item)
    paid = models.BooleanField(default=True)
    suspicious = models.BooleanField(default=False)
