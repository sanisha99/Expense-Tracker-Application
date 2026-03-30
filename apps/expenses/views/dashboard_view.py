from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from apps.expenses.models import Expense, Category, Budget, Receipt

def dashboard(request):

    expenses = Expense.objects.all()

    date_range = request.GET.get("dates")

    if date_range and date_range != "None" and " to " in date_range:
        start_date, end_date = date_range.split(" to ")
        expenses = expenses.filter(date__range=[start_date, end_date])

    total_expenses = expenses.aggregate(total=Sum("amount"))["total"] or 0
    total_records = expenses.count()
    total_categories = expenses.values("category").distinct().count()
    total_spending = total_expenses

    category_data = expenses.values("category__name").annotate(total=Sum("amount"))

    category_labels = []
    category_values = []

    for item in category_data:
        category_labels.append(item["category__name"])
        category_values.append(float(item["total"]))

    monthly_data = (
        expenses.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    monthly_labels = []
    monthly_values = []

    for item in monthly_data:
        monthly_labels.append(item["month"].strftime("%b %Y"))
        monthly_values.append(float(item["total"]))
    
    today = timezone.now()

    current_month_expenses = Expense.objects.filter(
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum("amount"))

    total_spent = current_month_expenses["total"] or 0

    budget = Budget.objects.filter(
    month__year=today.year,
    month__month=today.month
    ).first()

    budget_message = None
    budget_level = None
    budget_percent = 0

    if budget and budget.budget_limit:

        limit = budget.budget_limit
        budget_percent = (total_spent / limit) * 100

        if budget_percent >= 100:
            budget_message = f"🚨 Budget exceeded! ({budget_percent:.0f}%)"
            budget_level = "danger"

        elif budget_percent >= 80:
            budget_message = f"⚠️ {budget_percent:.0f}% of budget used"
            budget_level = "high"

        elif budget_percent >= 70:
            budget_message = f"⚠️ {budget_percent:.0f}% budget usage"
            budget_level = "medium"

        elif budget_percent >= 50:
            budget_message = f"ℹ️ {budget_percent:.0f}% of budget used"
            budget_level = "low"

    context = {
        "total_expenses": total_expenses,
        "total_records": total_records,
        "total_categories": total_categories,
        "total_spending": total_spending,
        "selected_dates": date_range,
        "category_labels": category_labels,
        "category_data": category_values,
        "monthly_labels": monthly_labels,
        "monthly_data": monthly_values,
        "budget_message": budget_message,
        "budget_level": budget_level,
        "budget_percent": budget_percent,
    }

    return render(request, "dashboard.html", context)
