import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render

@csrf_exempt
def chat_view(request):
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []

    if request.method == 'POST':
        user_input = request.POST.get('message', '').strip().lower()

        # Check if the request is to clear the chat history
        if request.POST.get('clear_history') == 'true':
            if 'chat_history' in request.session:
                del request.session['chat_history']
            return JsonResponse({"status": "success", "message": "Chat history cleared"})

        # --- New custom response logic starts here ---
        custom_response = None
        if user_input in ["what do i call you??", "what is your name?", "who are you?"]:
            custom_response = "I am ChatMCA"
        
        if custom_response:
            request.session['chat_history'].append({"role": "user", "content": request.POST.get('message', '')})
            request.session['chat_history'].append({"role": "assistant", "content": custom_response})
            request.session.modified = True
            return JsonResponse({"chat_history": request.session['chat_history']})
        # --- New custom response logic ends here ---

        # Add the user's message to the chat history
        request.session['chat_history'].append({"role": "user", "content": request.POST.get('message', '')})
        request.session.modified = True

        try:
            genai.configure(api_key="AIzaSyCWp3sMwUR0NNIF80pPkW3xlmz8mEQj2_A")
            model = genai.GenerativeModel('gemini-2.5-flash')

            gemini_history = []
            for msg in request.session['chat_history']:
                role = "model" if msg['role'] == 'assistant' else "user"
                gemini_history.append({'role': role, 'parts': [msg['content']]})

            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(request.POST.get('message', ''))
            assistant_response = response.text

            request.session['chat_history'].append({"role": "assistant", "content": assistant_response})
            request.session.modified = True
            
            return JsonResponse({"chat_history": request.session['chat_history']})

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            return JsonResponse({"error": error_message}, status=500)

    return render(request, 'chat.html', {'chat_history': request.session['chat_history']})