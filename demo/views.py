from django.shortcuts import render
from .rdata import robots
from .rdata import movies


# Create your views here.


def index(request):
    # a = "Good Afternoon"
    # b = "This is my first Django project"
    # print(robots[0].get("name"))
    return render(request, 'index.html')
    # return render(request, 'index.html', {"robots": robots})
    # return render(request, 'index.ejs', {"robots": robots})
    # return render(request, 'index.html',{"aa":a,"bb":b})
    # return render(request, 'robo.html', {"robots": robots})

def robo(request):
    return render(request, 'robo.html', {"robots": robots})

def movie(request):
    return render(request, 'movies.html', {"movies": movies})