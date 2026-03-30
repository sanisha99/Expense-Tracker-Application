from datetime import date
from decimal import Decimal
import re

from apps.expenses.models import Expense, Category


# =========================
# INIT FLOW
# =========================
def init_flow():
    return {
        "step": "item",
        "data": {
            "item": None,
            "amount": None,
            "category": None,
            "date": None,
            "tax_rate": 0
        }
    }


# =========================
# HANDLE FLOW
# =========================
def handle_flow(flow, query, user):

    print("FLOW STEP:", flow["step"], "| INPUT:", query)

    step = flow["step"]

    # -------------------------
    # ITEM
    # -------------------------
    if step == "item":
        cleaned = query.lower().replace("add", "").replace("expense", "").strip()
        flow["data"]["item"] = cleaned
        flow["step"] = "amount"
        return flow, "What is the amount?"

    # -------------------------
    # AMOUNT
    # -------------------------
    if step == "amount":
        cleaned = re.sub(r"[^\d.]", "", query)
        print("CLEANED AMOUNT:", cleaned)

        if not cleaned:
            return flow, "Enter valid amount (e.g., 50)"

        flow["data"]["amount"] = cleaned
        flow["step"] = "category"
        return flow, "Which category?"
        

    # -------------------------
    # CATEGORY
    # -------------------------
    if step == "category":
        cleaned = query.lower().replace("for", "").strip()

        category = Category.objects.filter(name__iexact=cleaned).first()

        if not category:
            category = Category.objects.create(name=cleaned)

        flow["data"]["category"] = cleaned
        flow["step"] = "date"

        return flow, "Enter date (YYYY-MM-DD or today)"

    # -------------------------
    # DATE
    # -------------------------
    if step == "date":

        if query.lower() == "today":
            flow["data"]["date"] = date.today().isoformat()
        else:
            try:
                # validate but store as string
                parsed_date = date.fromisoformat(query)
                flow["data"]["date"] = parsed_date.isoformat()
            except:
                return flow, "Invalid date format"

        flow["step"] = "tax"
        return flow, "Enter tax rate (or 0)"

    # -------------------------
    # TAX + SAVE
    # -------------------------
    if step == "tax":

        try:
            tax_rate = Decimal(query)
        except:
            return flow, "Enter valid number"

        data = flow["data"]

        try:
            amount = Decimal(data["amount"])

            category_obj = Category.objects.filter(
                name__iexact=data["category"]
            ).first()

            if not category_obj:
                category_obj = Category.objects.create(name=data["category"])

            date_obj = date.fromisoformat(data["date"])

            tax_amount = (amount * tax_rate) / 100

            Expense.objects.create(
                item=data["item"],
                amount=amount,
                category=category_obj,
                date=date_obj,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                created_by=user
            )

            # ✅ MOVE RETURN INSIDE TRY
            return None, f"Added {data['item']} (${amount}) successfully"

        except Exception as e:
            print("SAVE ERROR:", str(e))
            return None, "Error saving expense"