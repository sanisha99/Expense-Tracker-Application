
# import google.generativeai as genai

# from django.shortcuts import render

# from django.conf import settings
# from django.http import JsonResponse
# from django.db.models import Sum 
# from .models import Expense,Budget
# from datetime import date

# import re
# import json

# # Configure Gemini
# genai.configure(api_key=settings.GOOGLE_API_KEY)
# model = genai.GenerativeModel("models/gemini-2.5-flash")


# def chatbot_view(request):
#     query = request.GET.get("q")

#     # UI load
#     if not query:
#         return render(request, "chatbot.html")

#     try:
#         expenses = Expense.objects.select_related("category").all()

#         documents = []
#         for exp in expenses:
#             doc = (
#                 f"Date: {exp.date}, "
#                 f"Category: {exp.category.name}, "
#                 f"Item: {exp.item}, "
#                 f"Amount: {exp.amount}, "
#                 f"Tax: {exp.tax_amount}"
#             )
#             documents.append(doc)

#         if not documents:
#             return JsonResponse({"answer": "No expense data available."})

#         context = "\n".join(documents[:100])

#         prompt = f"""
# You are a financial assistant.

# Use ONLY the data below:

# {context}

# Question: {query}

# Answer clearly with numbers.
# """

#         response = model.generate_content(prompt)

#         return JsonResponse({"answer": response.text})

#     except Exception as e:
#         return JsonResponse({"answer": f"Error: {str(e)}"})
    



# import google.generativeai as genai
# import json

# from datetime import date

# from django.shortcuts import render
# from django.conf import settings
# from django.http import JsonResponse
# from django.db.models import Sum

# from .models import Expense, Budget


# # Configure Gemini
# genai.configure(api_key=settings.GOOGLE_API_KEY)
# model = genai.GenerativeModel("models/gemini-2.5-flash")


from apps.expenses.services.flow_service import init_flow, handle_flow
from apps.expenses.services.chatbot_service import handle_query
from django.http import JsonResponse
from django.shortcuts import render

def chatbot_view(request):

    if not request.GET.get("q"):
        return render(request, "chatbot.html", {
            "chat_history": request.session.get("chat_history", [])
        })

    query = request.GET.get("q").strip()

    chat_history = request.session.get("chat_history", [])
    flow = request.session.get("flow")
    last_context = request.session.get("last_context")

    chat_history.append({"role": "user", "message": query})

    try:

        # START FLOW
        if query.lower().startswith("add"):
            flow = init_flow()
            request.session["flow"] = flow
            return JsonResponse({"answer": "What is the item?"})

        # HANDLE FLOW
        if flow:
            flow, response = handle_flow(flow, query, request.user)

            if flow:
                request.session["flow"] = flow
            else:
                del request.session["flow"]

            return JsonResponse({"answer": response})

        # NORMAL QUERY
        result = handle_query(query, last_context)

        if isinstance(result, dict):
            response = result["response"]
            request.session["last_context"] = result["context"]
        else:
            response = result

        chat_history.append({"role": "assistant", "message": response})
        request.session["chat_history"] = chat_history

        return JsonResponse({"answer": response})

    except Exception as e:
        print("ERROR:", str(e))
        return JsonResponse({"answer": "Something went wrong"})