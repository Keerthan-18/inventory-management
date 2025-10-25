from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from datetime import date, timedelta
import os
import google.generativeai as genai
from dotenv import load_dotenv
from django.conf import settings

load_dotenv()
genai.configure(api_key=settings.GOOGLE_API_KEY)
# AIzaSyBQRwJ

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




from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import google.generativeai as genai

@csrf_exempt
def ai_query(request):
    if request.method == 'POST':
        user_query = request.POST.get('query', "").strip()

        try:
            
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            medicines = Medicine.objects.all()
            medicine_data = "\n".join(
                [f"{m.name} | {m.category} | Qty: {m.quantity} | Price: ₹{m.price} | Expiry: {m.expiry_date}"
                 for m in medicines]
            )

            inventory_keywords = ["stock", "quantity", "available", "expired", "expiring", "price", "low stock"]
            is_inventory_related = any(word in user_query.lower() for word in inventory_keywords)

            # Create context-aware system prompt
            if is_inventory_related:
                prompt = f"""
                You are MedAI, an intelligent pharmacy assistant managing this medicine inventory:

                {medicine_data}

                The user asked: "{user_query}"

                Using the data above, respond ONLY with medicines that match the question.
                - Show results in a neat readable list or table format.
                - Use bullet points (•) and line breaks for clarity.
                - Do NOT make up medicines that are not in the list.
                - Example: “• Paracetamol — Qty: 12 | Expiry: 2026-04-12 | Price: ₹25.00”
                """
            else:
                prompt = f"""
                You are MedAI, a trusted pharmacy and medical guidance assistant.

                The user asked: "{user_query}"

                Provide a clear, medically sound, and concise answer about:
                - When the medicine should be prescribed
                - How often to take it
                - Whether before or after meals
                - Any common precautions or warnings.

                Make your response short, professional, and easy to read (use bullet points where needed).
                """

            #  Generate Gemini response
            response = model.generate_content(prompt)
            formatted_reply = response.text.replace("₹", "₹ ")  # small spacing fix
            return JsonResponse({'reply': formatted_reply})

        except Exception as e:
            return JsonResponse({'error': str(e)})

    return HttpResponse('AI endpoint. Please send a POST request.')


def list_models(request):
    try:
        models = list(genai.list_models())
        model_names = [m.name for m in models]  # Extract model names
        return JsonResponse({"available_models": model_names})
    except Exception as e:
        return JsonResponse({"error": str(e)})
 






        


