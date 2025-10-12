from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from datetime import date, timedelta

from .models import Medicine
from .forms import MedicineForm

# For API
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import MedicineSerializer
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta



@login_required
def medicine_list(request):
    query = request.GET.get('q')   # Get search text if user searched
    medicines = Medicine.objects.all()

    # Apply search filter (if query exists)
    if query:
        medicines = medicines.filter(name__icontains=query) | medicines.filter(category__icontains=query)
        
    # Check low stock & expiry alerts
    today = date.today()
    for med in medicines:
        med.low_stock = med.quantity < 10  # Alert if quantity < 10
        med.expiring_soon = med.expiry_date <= today + timedelta(days=30)  # Alert if expiring in next 30 days

    return render(request, 'inventory/medicine_list.html', {
        'medicines': medicines,
        'query': query
    })

@login_required
def medicine_add(request):
    if request.method == "POST":
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('medicine_list')
    else:
        form = MedicineForm()
    return render(request, 'inventory/medicine_form.html', {'form': form})

@login_required
def medicine_edit(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == "POST":
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            return redirect('medicine_list')
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'inventory/medicine_form.html', {'form': form})

@login_required
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        medicine.delete()
        return redirect('medicine_list')
    return render(request, 'inventory/medicine_delete.html', {'medicine': medicine})


# API End Point

@api_view(['GET'])
def api_medicines(request):
    medicines = Medicine.objects.all()
    serializer = MedicineSerializer(medicines, many=True)
    return Response(serializer.data)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def ai_query(request):
    from datetime import date
    today = date.today()
    ai_response = ""

    if request.method == "POST":
        query = request.POST.get("query", "").lower()

        
        if "low stock" in query:
            low_items = Medicine.objects.filter(quantity__lt=10)
            if low_items.exists():
                ai_response = "Low stock medicines: " + ", ".join(m.name for m in low_items)
            else:
                ai_response = "All medicines are sufficiently stocked."

        
        elif "expired" in query:
            expired = Medicine.objects.filter(expiry_date__lt=today)
            if expired.exists():
                ai_response = "Expired medicines: " + ", ".join(m.name for m in expired)
            else:
                ai_response = "No medicines are expired."

        
        elif "expiring soon" in query:
            from datetime import timedelta
            soon = Medicine.objects.filter(expiry_date__lte=today + timedelta(days=30), expiry_date__gte=today)
            if soon.exists():
                ai_response = "Expiring soon: " + ", ".join(m.name for m in soon)
            else:
                ai_response = "No medicines expiring within 30 days."

        
        elif "how many" in query:
            words = query.split()
            for med in Medicine.objects.all():
                if med.name.lower() in query:
                    ai_response = f"There are {med.quantity} units of {med.name} left."
                    break
            if not ai_response:
                ai_response = "I couldn’t find that medicine in inventory."

        
        else:
            ai_response = "Sorry, I didn’t understand. Try asking things like 'low stock', 'expired', or 'how many Paracetamol left'."

    
    medicines = Medicine.objects.all()
    return render(request, "inventory/medicine_list.html", {"medicines": medicines, "ai_response": ai_response})

        

        


