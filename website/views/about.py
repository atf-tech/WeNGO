from django.shortcuts import render,redirect
from django.shortcuts import render, get_object_or_404
from website.views import *




def about(request):
    
    return render(request, 'website/about.html')