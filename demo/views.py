from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm # Import AuthenticationForm
from .rdata import robots
from .rdata import movies
from .forms import RegisterForm, LoginForm # Import LoginForm

# Create your views here.


def index(request):
    return render(request, 'index.html')

def robo(request):
    return render(request, 'robo.html', {"robots": robots})

def movie(request):
    query = request.GET.get("user_input")

    if query:
        mymovies = [
            movie for movie in movies 
            if query.lower() in movie['name'].lower() or 
               query.lower() in movie['genre'].lower() or 
               query == str(movie['releaseYear'])
        ]
        
        if not mymovies:
            mymovies = [{"name": "No results found", "genre": "", "releaseYear": ""}]
    else:
        mymovies = movies

    return render(request, 'movies.html', {"movies": mymovies})

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('ChatMCA')  # Redirect to your chat page after registration
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})

def combined_login_register(request):
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        if 'login_submit' in request.POST: # Check if login form was submitted
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('ChatMCA')
                else:
                    login_form.add_error(None, "Invalid username or password.")
        elif 'register_submit' in request.POST: # Check if register form was submitted
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                return redirect('ChatMCA')
    
    return render(request, 'login_register_content.html', { # Changed template name here
        'login_form': login_form,
        'register_form': register_form
    })