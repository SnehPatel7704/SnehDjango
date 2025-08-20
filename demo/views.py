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
    query = request.GET.get("user_input")

    if query:
        mymovies = [movie for movie in movies if query.lower() in movie['name'].lower()]
        # print(mymovies)
        if not mymovies:
            mymovies = [{"name": "No results found", "genre": "", "releaseYear": ""}]
    else:
        mymovies = movies

    return render(request, 'movies.html', {"movies": mymovies})
    # return render(request, 'movies.html')