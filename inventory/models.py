from django.db import models
from datetime import date, timedelta



class Medicine(models.Model):
    name=models.CharField(max_length=100)
    category=models.CharField(max_length=50)
    quantity=models.IntegerField()
    price=models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date=models.DateField()
    reorder_level=models.IntegerField(default=10)
    
    def __str__(self):
        return self.name
    
    @property
    def low_stock(self):
        return self.quantity < (self.reorder_level or 10)

    @property
    def expiring_soon(self):
        return self.expiry_date <= date.today().replace(day=date.today().day) + timedelta(days=30)

