from django.shortcuts import render

# Create your views here.
def inbox(request):
    return render(request, 'inbox.html')

def whatsapp_chat(request):
    return render(request, 'whatsapp_chat.html')

def all_transaction(request):
    return render(request, 'all_transaction.html')

def add_gpay_payments(request):
    return render(request, 'add_gpay_payments.html')