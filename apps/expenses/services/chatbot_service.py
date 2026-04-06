from apps.expenses.services import expense_service
from apps.expenses.models import Category,Expense
from google import genai
from django.conf import settings
import json
import re
from datetime import datetime
from django.db.models import Sum

client = genai.Client(api_key=settings.GOOGLE_API_KEY)


def parse_intent(query):
    prompt = f"""
    You are a strict JSON API.

    Return ONLY valid JSON.
    No explanation.

    Allowed intents:
    total_spending, category_spending, item_breakdown, list_items,
    item_prices, highest_expense, latest_expense,
    top_items, recent_expenses, monthly_spending,
    budget_summary, add_expense

    Rules:
    - "highest", "maximum" → highest_expense
    - "latest", "recent" → latest_expense
    - "prices", "amount" → item_prices
    - "this month" → month = "this_month"
    - "last month" → month = "last_month"
    - breakdown/list/items + "this month" → intent = item_breakdown, month = "this_month"

    Format:
    {{
    "intent": "...",
    "entities": {{
        "category": null,
        "item": null,
        "amount": null,
        "month": null
    }}
    }}

    Examples:
    Query: "highest expense item"
    {{"intent": "highest_expense", "entities": {{"category": null, "item": null, "amount": null, "month": null}}}}

    Query: "total expense this month"
    {{"intent": "total_spending", "entities": {{"category": null, "item": null, "amount": null, "month": "this_month"}}}}

    If unsure:
    {{"intent": "unknown", "entities": {{}}}}

    Query: {query}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = response.text.strip()
        print("RAW GEMINI:", text)

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())

        return {"intent": "unknown", "entities": {}}

    except Exception as e:
        print("AI ERROR:", str(e))
        return {
            "intent": "error",
            "entities": {},
            "message": "AI is currently busy. Please try again in a few seconds."
        }


def format_response(data):
    prompt = f"""
    Convert this JSON into a natural friendly response.

    Rules:
    - Keep it short
    - Do NOT change numbers
    - Do NOT add new info

    Data:
    {json.dumps(data)}
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response.text.strip()


def extract_category(query, user):
    # ← now filters by user
    for cat in Category.objects.filter(created_by=user).values_list("name", flat=True):
        if cat.lower() in query.lower():
            return cat
    return None


# =========================
# MAIN QUERY HANDLER
# =========================

def handle_query(intent, entities, last_context, user=None):

    category = entities.get("category")
    month = entities.get("month")
    now = datetime.now()
    
    filter_month = None
    filter_year = None

    if month == "this_month":
        filter_month = now.month
        filter_year = now.year
    elif month == "last_month":
        if now.month == 1:
            filter_month = 12
            filter_year = now.year - 1
        else:
            filter_month = now.month - 1
            filter_year = now.year

    # -------------------------
    # TOTAL SPENDING
    # -------------------------
    if intent == "total_spending":
        if month == "this_month":
            total = expense_service.get_total_spending(
                user=user,
                category=category,
                month=now.month,
                year=now.year
            )
        else:
            total = expense_service.get_total_spending(
                user=user,
                category=category
            )

        return {
            "intent": intent,
            "data": {
                "total": float(total),
                "category": category,
                "month": month
            }
        }

    # -------------------------
    # CATEGORY SPENDING
    # -------------------------
    if intent == "category_spending":
        total = expense_service.get_category_spending(
            user=user,
            category=category
        )
        return {
            "intent": intent,
            "data": {
                "category": category,
                "total": float(total)
            }
        }

    # -------------------------
    # ITEM BREAKDOWN / LIST
    # -------------------------
    if intent in ["item_breakdown", "list_items"]:
        qs = Expense.objects.filter(created_by=user) if user else Expense.objects.all()

        if category:
            qs = qs.filter(category__name__iexact=category)

        # ← Apply month filter here
        if filter_month and filter_year:
            qs = qs.filter(date__month=filter_month, date__year=filter_year)

        qs = qs.exclude(item__isnull=True).exclude(item="")

        data = list(
            qs.values("item")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:10]
        )

        return {
            "intent": intent,
            "data": [{"item": i["item"], "total": float(i["total"])} for i in data],
            "context": {"category": category}
        }

    # -------------------------
    # ITEM PRICES (FOLLOW-UP)
    # -------------------------
    if intent == "item_prices":
        if not category and last_context:
            category = last_context.get("category")

        if not category:
            return {"intent": intent, "data": "Please specify a category"}

        data = [
            {"item": i["item"], "total": float(i["total"])}
            for i in expense_service.get_item_breakdown(user=user, category=category)
        ]
        return {"intent": intent, "data": data}

    # -------------------------
    # HIGHEST EXPENSE
    # -------------------------
    if intent == "highest_expense":
        expense = expense_service.get_highest_expense(user=user, category=category)

        if not expense:
            return {"intent": intent, "data": "No data found"}

        return {
            "intent": intent,
            "data": {
                "item": expense.item,
                "amount": float(expense.amount)
            }
        }

    # -------------------------
    # LATEST EXPENSE
    # -------------------------
    if intent == "latest_expense":
        expense = expense_service.get_latest_expense(user=user, category=category)

        if not expense:
            return {"intent": intent, "data": "No data found"}

        return {
            "intent": intent,
            "data": {
                "item": expense.item,
                "amount": float(expense.amount),
                "date": str(expense.date)
            }
        }

    # -------------------------
    # TOP ITEMS
    # -------------------------
    if intent == "top_items":
        qs = Expense.objects.filter(created_by=user) if user else Expense.objects.all()

        if category:
            qs = qs.filter(category__name__iexact=category)

        if filter_month and filter_year:
            qs = qs.filter(date__month=filter_month, date__year=filter_year)

        qs = qs.exclude(item__isnull=True).exclude(item="")

        data = list(
            qs.values("item")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )

        return {
            "intent": intent,
            "data": [{"item": i["item"], "total": float(i["total"])} for i in data]
        }
    
    # -------------------------
    # RECENT EXPENSES
    # -------------------------

    if intent == "recent_expenses":
        qs = Expense.objects.filter(created_by=user) if user else Expense.objects.all()

        if filter_month and filter_year:
            qs = qs.filter(date__month=filter_month, date__year=filter_year)

        from django.db.models import Sum
        data = list(
            qs.order_by("-date").values("item", "amount", "date")[:10]
        )

        return {
            "intent": intent,
            "data": [
                {"item": i["item"], "amount": float(i["amount"]), "date": str(i["date"])}
                for i in data
            ]
        }

    

    # -------------------------
    # MONTHLY TREND
    # -------------------------
    if intent == "monthly_spending":
        data = expense_service.get_monthly_spending(user=user)
        return {
            "intent": intent,
            "data": [
                {
                    "month": str(i["month"]),
                    "total": float(i["total"])
                }
                for i in data
            ]
        }

    # -------------------------
    # BUDGET SUMMARY
    # -------------------------
    if intent == "budget_summary":
        summary = expense_service.get_budget_summary(user=user)

        if not summary:
            return {"intent": intent, "data": "No budget set"}

        return {"intent": intent, "data": summary}

    # -------------------------
    # ADD EXPENSE
    # -------------------------
    if intent == "add_expense":
        return {"intent": intent, "data": entities}

    # -------------------------
    # DEFAULT
    # -------------------------
    return {
        "intent": "unknown",
        "data": "Sorry, I didn't understand that."
    }