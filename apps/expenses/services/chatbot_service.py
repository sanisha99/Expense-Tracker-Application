from apps.expenses.services import expense_service
from apps.expenses.models import Category


# =========================
# CATEGORY DETECTION
# =========================
def extract_category(query):
    for cat in Category.objects.values_list("name", flat=True):
        if cat.lower() in query.lower():
            return cat
    return None


# =========================
# MAIN QUERY HANDLER
# =========================
def handle_query(query, last_context):

    q = query.lower()
    category = extract_category(query)

    # -------------------------
    # FOLLOW-UP (prices)
    # -------------------------
    if "price" in q or "amount" in q:

        if not category and last_context:
            category = last_context.get("category")

        if not category:
            return "Please specify a category"

        data = expense_service.get_item_breakdown(category)

        return ", ".join(
            [f"{i['item']}: ${i['total']}" for i in data]
        ) or "No data found"

    # -------------------------
    # ITEMS
    # -------------------------
    if "item" in q or "list" in q:

        data = expense_service.get_item_breakdown(category)

        return {
            "response": ", ".join([i["item"] for i in data]) or "No items found",
            "context": {"category": category}
        }

    # -------------------------
    # TOTAL
    # -------------------------
    if "total" in q:

        total = expense_service.get_total_spending(category)

        return f"Total spending is ${total}"

    return "Sorry, I didn’t understand that."