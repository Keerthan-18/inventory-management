from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from datetime import date, timedelta
import os, re
import google.generativeai as genai
from dotenv import load_dotenv
from django.conf import settings
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Medicine
from .forms import MedicineForm
from .serializers import MedicineSerializer
from django.views.decorators.csrf import csrf_exempt


load_dotenv()

genai.configure(api_key=settings.GOOGLE_API_KEY)



@login_required
def medicine_list(request):
    query = request.GET.get('q')
    medicines = Medicine.objects.all()

    if query:
        medicines = medicines.filter(name__icontains=query) | medicines.filter(category__icontains=query)

    today = date.today()
    for med in medicines:
        med.is_low_stock = med.quantity < 150
        med.is_expiring_soon = med.expiry_date <= today + timedelta(days=30)

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
            messages.success(request, "Medicine added successfully!")
            return redirect('medicine_list')
        else:
            messages.error(request, "Error adding medicine. Please check the form.")
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
            messages.success(request, "Medicine updated successfully!")
            return redirect('medicine_list')
        else:
            messages.error(request, "Error updating medicine.")
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'inventory/medicine_form.html', {'form': form})


@login_required
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        medicine.delete()
        messages.success(request, "Medicine deleted successfully!")
        return redirect('medicine_list')
    return render(request, 'inventory/medicine_delete.html', {'medicine': medicine})


@api_view(['GET'])
def api_medicines(request):
    medicines = Medicine.objects.all()
    serializer = MedicineSerializer(medicines, many=True)
    return Response(serializer.data)


def test_gemini(request):
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Hello Gemini, are you working?")
        return JsonResponse({'reply': response.text})
    except Exception as e:
        return JsonResponse({"error": str(e)})


@csrf_exempt
def ai_query(request):
    """MedAI — Smart pharmacy assistant using Gemini AI."""
    if request.method != "POST":
        return HttpResponse("AI endpoint. Please send a POST request.")

    user_query = (request.POST.get("query") or "").strip()
    uq_lower = user_query.lower()

    quantity_keywords = ["how many", "left", "quantity", "qty", "units"]
    reorder_keywords = ["reorder", "restock", "low stock", "below reorder"]
    expiry_keywords = ["expire", "expiring", "expiry", "expiration"]
    medical_keywords = [
        "prescribe", "dosage", "take", "before meal", "after meal",
        "how many times", "use for", "side effect", "tablet", "capsule", "medicine"
    ]

    try:
        medicines = Medicine.objects.all()
        medicine_data = "\n".join([
            f"{m.name} | Category: {m.category} | Qty: {m.quantity} | "
            f"Reorder Level: {m.reorder_level} | Price: ₹{m.price} | Expiry: {m.expiry_date}"
            for m in medicines
        ])

        if any(kw in uq_lower for kw in quantity_keywords):
            found_med = next((m for m in medicines if m.name.lower() in uq_lower), None)
            if found_med:
                reply = f"There are <strong>{found_med.quantity}</strong> units of <strong>{found_med.name}</strong> left in stock."
                if found_med.quantity < found_med.reorder_level:
                    reply += f" This is below the reorder level ({found_med.reorder_level}). Please restock soon."
                return JsonResponse({"reply": reply})
            return JsonResponse({"reply": "I couldn’t find that medicine in the inventory."})

        if any(kw in uq_lower for kw in reorder_keywords):
            low_stock_meds = Medicine.objects.filter(quantity__lt=models.F("reorder_level"))
            if not low_stock_meds:
                return JsonResponse({"reply": "All medicines are above their reorder levels."})
            formatted = "<br>".join([
                f"• <strong>{m.name}</strong> — Qty: {m.quantity}, Reorder Level: {m.reorder_level}"
                for m in low_stock_meds
            ])
            reply = f"<strong>Medicines that need restocking:</strong><br>{formatted}"
            return JsonResponse({"reply": reply})

        if any(kw in uq_lower for kw in expiry_keywords):
            today = date.today()
            expiring = Medicine.objects.filter(expiry_date__lte=today + timedelta(days=30))
            if not expiring:
                return JsonResponse({"reply": "No medicines are expiring soon."})
            formatted = "<br>".join([
                f"• <strong>{m.name}</strong> — Expiry: {m.expiry_date}, Qty: {m.quantity}"
                for m in expiring
            ])
            reply = f"<strong>Medicines expiring soon (within 30 days):</strong><br>{formatted}"
            return JsonResponse({"reply": reply})

        if any(kw in uq_lower for kw in medical_keywords):
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            prompt = f"""
You are MedAI, a professional and safety-focused pharmacy assistant.
You have access to this inventory data:

{medicine_data}

User Question: "{user_query}"

If the medicine exists, mention its quantity and expiry.
Then give general medical info (uses, dosage, precautions).
End with:
"This info is for educational purposes only. Consult a doctor before use."
"""
            response = model.generate_content(prompt)
            text = (response.text or "").replace("\\u20b9", "₹").strip()
            return JsonResponse({"reply": text})

        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(f"User: {user_query}\nInventory:\n{medicine_data}")
        return JsonResponse({"reply": response.text.strip()})

    except Exception as e:
        return JsonResponse({"error": str(e)})


def list_models(request):
    try:
        models_list = list(genai.list_models())
        model_names = [m.name for m in models_list]
        return JsonResponse({"available_models": model_names})
    except Exception as e:
        return JsonResponse({"error": str(e)})



@login_required
def dashboard(request):
    today = date.today()
    total_medicines = Medicine.objects.count()
    low_stock_count = Medicine.objects.filter(quantity__lt=10).count()
    expiring_soon_count = Medicine.objects.filter(expiry_date__lte=today + timedelta(days=30)).count()
    healthy_count = total_medicines - low_stock_count - expiring_soon_count

    category_stats = Medicine.objects.values('category').annotate(
        total_qty=models.Sum('quantity'),
        avg_price=models.Avg('price')
    )

    top_medicines = Medicine.objects.order_by('-quantity')[:5]

    categories = [c['category'] for c in category_stats]
    quantities = [c['total_qty'] for c in category_stats]
    avg_prices = [round(c['avg_price'], 2) for c in category_stats]

    context = {
        'total_medicines': total_medicines,
        'low_stock_count': low_stock_count,
        'expiring_soon_count': expiring_soon_count,
        'healthy_count': healthy_count,
        'categories': categories,
        'quantities': quantities,
        'avg_prices': avg_prices,
        'top_medicines': top_medicines,
    }

    return render(request, "inventory/dashboard.html", context)
