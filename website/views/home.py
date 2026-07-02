from django.shortcuts import render



def food(request):
    return render(request, 'website/food.html')