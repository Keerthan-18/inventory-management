from django.db import models


class Medicine(models.Model):
    name=models.CharField(max_length=100)
    category=models.CharField(max_length=50)
    quantity=models.IntegerField()
    price=models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date=models.DateField()
    
    def __str__(self):
        return self.name

