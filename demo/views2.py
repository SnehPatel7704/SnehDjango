# demo/views.py

import os
import uuid
import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings

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

def get_or_create_session_data(request):
    if 'chat_sessions' not in request.session:
        request.session['chat_sessions'] = []
        request.session['active_chat_id'] = None

    if not request.session['chat_sessions']:
        new_chat_id = str(uuid.uuid4())
        request.session['chat_sessions'].append({
            "id": new_chat_id,
            "title": "New Chat",
            "history": []
        })
        request.session['active_chat_id'] = new_chat_id
        request.session.modified = True

def get_active_chat(request):
    active_id = request.session.get('active_chat_id')
    if not active_id:
        return None
    for session in request.session['chat_sessions']:
        if session['id'] == active_id:
            return session
    return None

@csrf_exempt
def chat_view(request):
    get_or_create_session_data(request)

    if request.method == 'POST':
        if not model:
            return JsonResponse({"error": "Generative AI model is not configured."}, status=500)

        action = request.POST.get('action')

        if action == 'new_chat':
            new_chat_id = str(uuid.uuid4())
            new_chat = {"id": new_chat_id, "title": "New Chat", "history": []}
            request.session['chat_sessions'].insert(0, new_chat)
            request.session['active_chat_id'] = new_chat_id
            request.session.modified = True
            return JsonResponse({"status": "success", "new_chat_id": new_chat_id, "sessions": request.session['chat_sessions']})

        if action == 'delete_chat':
            chat_id = request.POST.get('chat_id')
            request.session['chat_sessions'] = [s for s in request.session['chat_sessions'] if s['id'] != chat_id]
            if request.session['active_chat_id'] == chat_id:
                if request.session['chat_sessions']:
                    request.session['active_chat_id'] = request.session['chat_sessions'][0]['id']
                else:
                    # If all chats are deleted, create a new one
                    get_or_create_session_data(request) # This will create a new default chat
            request.session.modified = True
            return JsonResponse({"status": "success", "sessions": request.session['chat_sessions'], "active_chat_id": request.session['active_chat_id']})

        if action == 'load_chat':
            chat_id = request.POST.get('chat_id')
            request.session['active_chat_id'] = chat_id
            request.session.modified = True
            active_chat = get_active_chat(request)
            return JsonResponse({"status": "success", "active_chat": active_chat})

        # Default action: process a message
        user_input = request.POST.get('message', '').strip()
        if not user_input:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)

        active_chat = get_active_chat(request)
        if not active_chat:
             return JsonResponse({"error": "No active chat session found."}, status=400)

        active_chat['history'].append({"role": "user", "content": user_input})
        
        # Generate a title for new chats
        if len(active_chat['history']) == 1 and active_chat['title'] == "New Chat":
            try:
                title_prompt = f"Generate a very short, concise title (3-5 words) for this user query: \"{user_input}\". Do not use quotes in the title."
                title_response = model.generate_content(title_prompt)
                active_chat['title'] = title_response.text.strip()
            except Exception as e:
                print(f"Error generating title: {e}")
                active_chat['title'] = user_input[:30] # Fallback title

        try:
            gemini_history = []
            for msg in active_chat['history'][:-1]:
                role = "model" if msg['role'] == 'assistant' else "user"
                gemini_history.append({'role': role, 'parts': [msg['content']]})
            
            chat_session = model.start_chat(history=gemini_history)
            response = chat_session.send_message(user_input)
            assistant_response = response.text

            active_chat['history'].append({"role": "assistant", "content": assistant_response})
            request.session.modified = True
            
            return JsonResponse({"active_chat": active_chat, "sessions": request.session['chat_sessions']})

        except Exception as e:
            error_message = f"An API error occurred: {str(e)}"
            return JsonResponse({"error": error_message}, status=500)

    # For GET requests
    active_chat = get_active_chat(request)
    return render(request, 'chat.html', {
        'chat_sessions': request.session.get('chat_sessions', []),
        'active_chat': active_chat
    })
