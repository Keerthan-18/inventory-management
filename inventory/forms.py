from django import forms
from .models import Medicine
from datetime import date

class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields=['name', 'category', 'quantity', 'price', 'expiry_date', 'reorder_level']


        def clean_expiry_date(self):
            expiry = self.cleaned_data["expiry_date"]
            if expiry < date.today():
                raise forms.ValidationError("Expiry date cannot be in the past.")
            return expiry

    def clean_quantity(self):
        qty = self.cleaned_data["quantity"]
        if qty < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return qty