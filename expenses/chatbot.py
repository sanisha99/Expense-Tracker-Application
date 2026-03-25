
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


import google.generativeai as genai
import json
import re

from datetime import date
from django.utils import timezone

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Sum

from .models import Expense, Budget, Category, Receipt

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")


def chatbot_view(request):
    query = request.GET.get("q")

    # -----------------------------
    # CHAT MEMORY (SESSION)
    # -----------------------------
    chat_history = request.session.get("chat_history", [])

    # Load UI
    if not query:
        return render(request, "chatbot.html", {"chat_history": chat_history})

    try:
        query_lower = query.lower()
        today = date.today()

        chat_history.append({"role": "user", "message": query})

        # -----------------------------
        # STEP 1: GET CATEGORIES
        # -----------------------------
        categories = list(
            Category.objects.values_list("name", flat=True).distinct()
        )

        # -----------------------------
        # STEP 2: INTENT EXTRACTION
        # -----------------------------
        intent_prompt = f"""
Convert the user query into a structured action.

Query: "{query}"

Available Tables:
- expense
- budget
- receipt
- category

Available Categories:
{categories}

Return ONLY JSON:

{{
  "action": "read | add",
  "table": "expense | budget | receipt | category",
  "operation": "sum | max | recent | breakdown | items | list",
  "filters": {{
    "category": "string or null",
    "time": "this_month | none"
  }},
  "data": {{
    "item": "string",
    "amount": number,
    "category": "string"
  }}
}}
"""

        intent_response = model.generate_content(intent_prompt)

        raw_text = intent_response.text.strip()
        cleaned_text = re.sub(r"```json|```", "", raw_text).strip()

        try:
            intent_data = json.loads(cleaned_text)
        except:
            intent_data = {
                "action": "read",
                "table": "expense",
                "operation": "sum",
                "filters": {"category": None, "time": "none"},
                "data": {}
            }

        action = intent_data.get("action", "read")
        table = intent_data.get("table", "expense")
        operation = intent_data.get("operation", "sum")
        filters = intent_data.get("filters", {})
        data = intent_data.get("data", {})

        category_name = filters.get("category")
        time_filter = filters.get("time", "none")

        # Manual override
        if "item" in query_lower or "items" in query_lower:
            operation = "items"

        # -----------------------------
        # STEP 3: ADD EXPENSE
        # -----------------------------
        if action == "add" and table == "expense":

            item = data.get("item")
            amount = data.get("amount")
            category_name = data.get("category")

            missing = []
            if not item:
                missing.append("item")
            if not amount:
                missing.append("amount")
            if not category_name:
                missing.append("category")

            if missing:
                return JsonResponse({
                    "answer": f"Please provide: {', '.join(missing)}"
                })

            category_obj, _ = Category.objects.get_or_create(name=category_name)

            Expense.objects.create(
                item=item,
                amount=amount,
                category=category_obj,
                tax_amount=0,
                tax_rate=0,
                date=date.today(),
                created_by=request.user if request.user.is_authenticated else None
            )

            return JsonResponse({
                "answer": f"Expense added successfully: {item} - {amount} ({category_name})"
            })

        # -----------------------------
        # STEP 4: EXPENSE DATA
        # -----------------------------
        if table == "expense":

            expenses = Expense.objects.select_related("category")

            if time_filter == "this_month":
                expenses = expenses.filter(
                    date__year=today.year,
                    date__month=today.month
                )

            if category_name:
                expenses = expenses.filter(category__name__iexact=category_name)

            context = ""

            if operation == "sum":
                total = expenses.aggregate(total=Sum("amount"))["total"] or 0
                context = f"""
Total Spending: {total}
Category: {category_name if category_name else "All"}
Time: {time_filter}
"""

            elif operation == "max":
                highest = expenses.order_by('-amount').first()
                if highest:
                    context = f"""
Highest Expense:
Item: {highest.item}
Category: {highest.category.name}
Amount: {highest.amount}
Date: {highest.date}
"""

            elif operation == "recent":
                latest = expenses.order_by('-date').first()
                if latest:
                    context = f"""
Most Recent Expense:
Item: {latest.item}
Category: {latest.category.name}
Amount: {latest.amount}
Date: {latest.date}
"""

            elif operation == "items":
                items = expenses.values("item", "amount")
                context = "Items:\n"
                for i in items:
                    context += f"{i['item']}: {i['amount']}\n"

            elif operation == "breakdown":
                if category_name:
                    items = expenses.values("item", "amount")
                    context = f"{category_name} breakdown:\n"
                    for i in items:
                        context += f"{i['item']}: {i['amount']}\n"
                else:
                    data_q = expenses.values("category__name").annotate(total=Sum("amount"))
                    context = "Category Breakdown:\n"
                    for i in data_q:
                        context += f"{i['category__name']}: {i['total']}\n"

        # -----------------------------
        # STEP 5: RECEIPT DATA
        # -----------------------------
        elif table == "receipt":

            receipts = Receipt.objects.all().order_by("-created_at")
            context = ""

            if operation == "recent":
                r = receipts.first()
                if r:
                    context = f"""
Latest Receipt:
Item: {r.item}
Total: {r.total_amount}
Tax: {r.tax_amount}
Date: {r.created_at}
"""

            elif operation == "items" or operation == "list":
                context = "Receipts:\n"
                for r in receipts[:10]:
                    context += f"{r.item}: {r.total_amount} ({r.created_at})\n"

        # -----------------------------
        # STEP 6: BUDGET DATA
        # -----------------------------
        elif table == "budget":

            today_dt = timezone.now()

            budget = Budget.objects.filter(
                month__year=today_dt.year,
                month__month=today_dt.month
            ).first()

            total_spent = Expense.objects.filter(
                date__year=today_dt.year,
                date__month=today_dt.month
            ).aggregate(total=Sum("amount"))["total"] or 0

            if budget:
                remaining = float(budget.budget_limit) - float(total_spent)

                context = f"""
Budget Summary:
Income: {budget.total_income}
Limit: {budget.budget_limit}
Spent: {total_spent}
Remaining: {remaining}
"""
            else:
                context = "No budget found."

        # -----------------------------
        # STEP 7: CATEGORY DATA
        # -----------------------------
        elif table == "category":

            cats = Category.objects.all()
            context = "Categories:\n"
            for c in cats:
                context += f"{c.name} - {c.subcategory}\n"

        # -----------------------------
        # STEP 8: FINAL RESPONSE
        # -----------------------------
        history_text = ""
        for chat in chat_history[-5:]:
            history_text += f"{chat['role']}: {chat['message']}\n"

        final_prompt = f"""
You are a financial assistant.

Use ONLY the data below.

Conversation:
{history_text}

Data:
{context}

Question: {query}

Answer clearly and confidently.
"""

        response = model.generate_content(final_prompt)

        chat_history.append({"role": "assistant", "message": response.text})
        request.session["chat_history"] = chat_history

        return JsonResponse({"answer": response.text})

    except Exception as e:
        return JsonResponse({"answer": f"Error: {str(e)}"})