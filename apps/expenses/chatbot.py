
from apps.expenses.services.flow_service import init_flow, handle_flow
from apps.expenses.services.chatbot_service import handle_query
from apps.expenses.services.chatbot_service import parse_intent, format_response
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
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

        # -------------------------
        # AI INTENT
        # -------------------------
        intent_data = parse_intent(query)

        intent = intent_data.get("intent")
        entities = intent_data.get("entities", {})

        # -------------------------
        # ADD EXPENSE (AI FIRST)
        # -------------------------
        if intent == "add_expense":
            if not entities.get("item") or not entities.get("amount") or not entities.get("category"):
                flow = init_flow()
                request.session["flow"] = flow

                return JsonResponse({
                    "answer": "Let’s add this step by step. What is the item?"
                })

     
        result = handle_query(intent, entities, last_context, user=request.user)
        print("FINAL RESULT:", result)
        # -------------------------
        # FORMAT RESPONSE (AI)
        # -------------------------
        if isinstance(result, dict):
            request.session["last_context"] = result.get("context")
            
            response = format_response(result)

        else:
            response = result

        chat_history.append({"role": "assistant", "message": response})
        request.session["chat_history"] = chat_history
    
        return JsonResponse({"answer": response})

    except Exception as e:
        import traceback
        traceback.print_exc()   

        return JsonResponse({
            "answer": f"Error: {str(e)}"
        })