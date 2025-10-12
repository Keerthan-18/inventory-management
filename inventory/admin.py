from django.contrib import admin
from .models import Medicine

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display=("name", "category", "quantity", "price", "expiry_date")
    search_fields=("name", "category")
    list_filter=("category", "expiry_date")
# Register your models here.
