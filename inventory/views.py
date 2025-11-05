from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from datetime import date, timedelta
import os
import google.generativeai as genai
from dotenv import load_dotenv
from django.conf import settings

load_dotenv()
genai.configure(api_key=settings.GOOGLE_API_KEY)


from django.http import JsonResponse
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
            return redirect('medicine_list')
        else:
            print(form.errors)
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
            print("Form errors:", form.errors)
            
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


def test_gemini(request):
    try:
        model=genai.GenerativeModel("gemini-2.5-flash")
        response=model.generate_content("Hello Gemini, are you working?")
        return JsonResponse({'reply': response.text})
    except Exception as e:
        return JsonResponse({"error": str(e)})



from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import re
from django.db import models

@csrf_exempt
def ai_query(request):
    if request.method != "POST":
        return HttpResponse("AI endpoint. Please send a POST request.")

    user_query = (request.POST.get('query') or "").strip()
    uq_lower = user_query.lower()

    medicines = Medicine.objects.all()

    if not medicines.exists():
        return JsonResponse({'reply': "The inventory is currently empty. Please add some medicines first."})




@csrf_exempt
def ai_query(request):
    """
    MedAI — Intelligent Pharmacy Assistant
    Gives complete, informative answers using both:
     1. Local inventory database (structured data)
     2. Gemini model (medical + natural language reasoning)
    """
    if request.method != "POST":
        return HttpResponse("AI endpoint. Please send a POST request.")

    user_query = (request.POST.get("query") or "").strip()
    uq_lower = user_query.lower()

    # Keyword groups for intent recognition
    quantity_keywords = ["how many", "left", "quantity", "qty", "units"]
    reorder_keywords = ["reorder", "restock", "low stock", "below reorder"]
    expiry_keywords = ["expire", "expiring", "expiry", "expiration"]
    medical_keywords = [
        "prescribe", "prescribed", "dosage", "dose", "take", "before meal",
        "after meal", "how many times", "when to give", "when should", "use for",
        "indication", "contraindication", "side effect", "side effects", "how to use",
        "tablet", "capsule", "medicine"
    ]

    try:
        # Load inventory data from database
        medicines = Medicine.objects.all()
        medicine_data = "\n".join(
            [
                f"{m.name} | Category: {m.category} | Qty: {m.quantity} | Reorder Level: {m.reorder_level} | Price: ₹{m.price} | Expiry: {m.expiry_date}"
                for m in medicines
            ]
        )

        #  INVENTORY QUERIES — "how many left" / "expiring soon" / "low stock"
        if any(kw in uq_lower for kw in quantity_keywords):
            found_med = None
            for m in medicines:
                if m.name.lower() in uq_lower:
                    found_med = m
                    break
            if found_med:
                reply = f"There are <strong>{found_med.quantity}</strong> units of <strong>{found_med.name}</strong> left in stock."
                if found_med.quantity < found_med.reorder_level:
                    reply += f"  This is below the reorder level ({found_med.reorder_level}). Please restock soon."
                return JsonResponse({"reply": reply})
            return JsonResponse({"reply": "I couldn’t find that medicine in the inventory."})

        if any(kw in uq_lower for kw in reorder_keywords):
            low_stock_meds = Medicine.objects.filter(quantity__lt=models.F("reorder_level"))
            if not low_stock_meds:
                return JsonResponse({"reply": " All medicines are above their reorder levels."})
            formatted = "<br>".join(
                [
                    f"• <strong>{m.name}</strong> — Qty: {m.quantity}, Reorder Level: {m.reorder_level}"
                    for m in low_stock_meds
                ]
            )
            reply = (
                "<strong>Medicines that need restocking:</strong><br>"
                f"{formatted}<br><br>"
                " Tip: Maintain at least twice the reorder level to avoid stockouts."
            )
            return JsonResponse({"reply": reply})

        if any(kw in uq_lower for kw in expiry_keywords):
            today = date.today()
            expiring = Medicine.objects.filter(expiry_date__lte=today + timedelta(days=30))
            if not expiring:
                return JsonResponse({"reply": " No medicines are expiring soon."})
            formatted = "<br>".join(
                [
                    f"• <strong>{m.name}</strong> — Expiry: {m.expiry_date}, Qty: {m.quantity}"
                    for m in expiring
                ]
            )
            reply = (
                "<strong>Medicines expiring soon (within 30 days):</strong><br>"
                f"{formatted}<br><br>"
                "Please follow FEFO (First Expire, First Out) to avoid wastage."
            )
            return JsonResponse({"reply": reply})

        if any(kw in uq_lower for kw in medical_keywords):
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            prompt = f"""
You are MedAI, a professional and safety-focused pharmacy assistant.
You have access to this inventory data:

{medicine_data}

User Question: "{user_query}"

Your task:
1. If the medicine exists in the inventory, mention its quantity and expiry.
2. Then give general medical details — its common uses, dosage, timing (before/after food), and precautions.
3. Keep tone clear, informative, and concise.
4. End with a safety note:
   " This information is for educational purposes only. Always consult a certified doctor or pharmacist before using any medicine."
"""
            response = model.generate_content(prompt)
            text = (response.text or "").replace("\\u20b9", "₹").strip()
            return JsonResponse({"reply": text})

        
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        prompt = f"""
You are MedAI, a pharmacy assistant integrated with an inventory system.
Here is the current inventory:
{medicine_data}

User question: "{user_query}"

If relevant, use inventory data to answer. Otherwise, give a short, helpful, and professional response related to pharmacy or medicines.
"""
        response = model.generate_content(prompt)
        text = (response.text or "").replace("\\u20b9", "₹").strip()
        return JsonResponse({"reply": text})

    except Exception as e:
        return JsonResponse({"error": str(e)})




def list_models(request):
    try:
        models = list(genai.list_models())
        model_names = [m.name for m in models]  # Extract model names
        return JsonResponse({"available_models": model_names})
    except Exception as e:
        return JsonResponse({"error": str(e)})

from django.db.models import Count, Avg
from datetime import date, timedelta

from django.db.models import Sum, Avg

@login_required
def dashboard(request):
    from datetime import date, timedelta
    from django.db.models import Sum, Avg

    today = date.today()
    total_medicines = Medicine.objects.count()
    low_stock_count = Medicine.objects.filter(quantity__lt=10).count()
    expiring_soon_count = Medicine.objects.filter(
        expiry_date__lte=today + timedelta(days=30)
    ).count()

    healthy_count = total_medicines - low_stock_count - expiring_soon_count

    category_stats = Medicine.objects.values('category').annotate(
        total_qty=Sum('quantity'),
        avg_price=Avg('price')
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


 






        


