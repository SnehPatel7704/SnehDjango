# demo/views.py

import os
import uuid
import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import ChatSession, ChatMessage

# --- Best Practice: Configure the API and Model Once ---
try:
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set in settings.py")
    genai.configure(api_key=api_key)

    SYSTEM_INSTRUCTION = "You are a helpful and friendly assistant named ChatMCA. Always respond in a polite and professional manner. You were developed by an MCA student named Sneh."

    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash-latest',
        system_instruction=SYSTEM_INSTRUCTION
    )
except (AttributeError, ValueError) as e:
    print(f"Error configuring Generative AI: {e}")
    model = None

# ---------------------------------------------------------

@login_required
@csrf_exempt
def chat_view(request):
    user = request.user
    
    # Ensure a user exists for testing purposes if not authenticated
    if not user.is_authenticated:
        # This part should ideally be handled by Django's authentication system
        # For demonstration, we'll get the first user or create one
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username='testuser', password='testpassword')
            user.save()

    # Get or create active chat session
    active_chat_id = request.session.get('active_chat_id')
    active_chat_session = None
    if active_chat_id:
        try:
            active_chat_session = ChatSession.objects.get(id=active_chat_id, user=user)
        except ChatSession.DoesNotExist:
            active_chat_session = None

    if not active_chat_session:
        # If no active chat or it doesn't exist, get the most recent one or create a new one
        active_chat_session = ChatSession.objects.filter(user=user).order_by('-created_at').first()
        if not active_chat_session:
            active_chat_session = ChatSession.objects.create(user=user, title="New Chat")
        request.session['active_chat_id'] = active_chat_session.id
        request.session.modified = True

    if request.method == 'POST':
        if not model:
            return JsonResponse({"error": "Generative AI model is not configured."}, status=500)

        action = request.POST.get('action')

        if action == 'new_chat':
            new_chat_session = ChatSession.objects.create(user=user, title="New Chat")
            request.session['active_chat_id'] = new_chat_session.id
            request.session.modified = True
            chat_sessions = ChatSession.objects.filter(user=user).order_by('-created_at')
            sessions_data = [{'id': chat.id, 'title': chat.title} for chat in chat_sessions]
            return JsonResponse({"status": "success", "new_chat_id": new_chat_session.id, "sessions": sessions_data})

        if action == 'delete_chat':
            chat_id = request.POST.get('chat_id')
            try:
                chat_to_delete = ChatSession.objects.get(id=chat_id, user=user)
                chat_to_delete.delete()
                
                # Set a new active chat if the deleted one was active
                if str(active_chat_session.id) == chat_id:
                    new_active_chat = ChatSession.objects.filter(user=user).order_by('-created_at').first()
                    if new_active_chat:
                        request.session['active_chat_id'] = new_active_chat.id
                    else:
                        # If no chats left, create a new one
                        new_active_chat = ChatSession.objects.create(user=user, title="New Chat")
                        request.session['active_chat_id'] = new_active_chat.id
                request.session.modified = True

                chat_sessions = ChatSession.objects.filter(user=user).order_by('-created_at')
                sessions_data = [{'id': chat.id, 'title': chat.title} for chat in chat_sessions]
                return JsonResponse({"status": "success", "sessions": sessions_data, "active_chat_id": request.session['active_chat_id']})
            except ChatSession.DoesNotExist:
                return JsonResponse({"error": "Chat session not found."}, status=404)

        if action == 'load_chat':
            chat_id = request.POST.get('chat_id')
            try:
                chat_to_load = ChatSession.objects.get(id=chat_id, user=user)
                request.session['active_chat_id'] = chat_to_load.id
                request.session.modified = True
                
                messages = chat_to_load.messages.all().order_by('created_at')
                active_chat_data = {
                    'id': chat_to_load.id,
                    'title': chat_to_load.title,
                    'history': [{'role': msg.role, 'content': msg.content} for msg in messages]
                }
                return JsonResponse({"status": "success", "active_chat": active_chat_data})
            except ChatSession.DoesNotExist:
                return JsonResponse({"error": "Chat session not found."}, status=404)

        # Default action: process a message
        user_input = request.POST.get('message', '').strip()
        if not user_input:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        if not active_chat_session:
             return JsonResponse({"error": "No active chat session found."}, status=400)

        # Save user message to database
        ChatMessage.objects.create(chat_session=active_chat_session, role="user", content=user_input)
        
        # Generate a title for new chats if it's the first message
        if active_chat_session.title == "New Chat" and active_chat_session.messages.count() == 1:
            try:
                title_prompt = f"Generate a very short, concise title (3-5 words) for this user query: \"{user_input}\". Do not use quotes in the title."
                title_response = model.generate_content(title_prompt)
                active_chat_session.title = title_response.text.strip()
                active_chat_session.save()
            except Exception as e:
                print(f"Error generating title: {e}")
                active_chat_session.title = user_input[:30] # Fallback title
                active_chat_session.save()

        try:
            # Retrieve full history for Gemini
            full_history = active_chat_session.messages.all().order_by('created_at')
            gemini_history = []
            for msg in full_history:
                role = "model" if msg.role == 'assistant' else "user"
                gemini_history.append({'role': role, 'parts': [msg.content]})
            
            # The last message is the current user_input, which should not be in history for start_chat
            # It should be sent as the current message
            chat_session_gemini = model.start_chat(history=gemini_history[:-1]) # Exclude the current user message
            response = chat_session_gemini.send_message(user_input)
            assistant_response = response.text

            # Save assistant response to database
            ChatMessage.objects.create(chat_session=active_chat_session, role="assistant", content=assistant_response)
            
            # Prepare active_chat data for JSON response
            updated_messages = active_chat_session.messages.all().order_by('created_at')
            active_chat_data = {
                'id': active_chat_session.id,
                'title': active_chat_session.title,
                'history': [{'role': msg.role, 'content': msg.content} for msg in updated_messages]
            }
            chat_sessions = ChatSession.objects.filter(user=user).order_by('-created_at')
            sessions_data = [{'id': chat.id, 'title': chat.title} for chat in chat_sessions]
            
            return JsonResponse({"active_chat": active_chat_data, "sessions": sessions_data})

        except Exception as e:
            error_message = f"An API error occurred: {str(e)}"
            return JsonResponse({"error": error_message}, status=500)

    # For GET requests
    chat_sessions = ChatSession.objects.filter(user=user).order_by('-created_at')
    sessions_data = [{'id': chat.id, 'title': chat.title} for chat in chat_sessions]
    
    active_chat_data = None
    if active_chat_session:
        messages = active_chat_session.messages.all().order_by('created_at')
        active_chat_data = {
            'id': active_chat_session.id,
            'title': active_chat_session.title,
            'history': [{'role': msg.role, 'content': msg.content} for msg in messages]
        }

    return render(request, 'chat.html', {
        'chat_sessions': sessions_data,
        'active_chat': active_chat_data
    })

