from django.shortcuts import render

def index(request):
    return render(request, 'wikimap/index.html')
