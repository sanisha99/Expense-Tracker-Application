from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
import json

from apps.expenses.models import Expense, Budget


@login_required
def dashboard(request):

    # -------------------------
    # USER FILTER
    # -------------------------
    expenses = Expense.objects.filter(created_by=request.user)

    # -------------------------
    # DATE FILTER
    # -------------------------
    date_range = request.GET.get("dates")

    if date_range and " to " in date_range:
        try:
            start_date, end_date = date_range.split(" to ")
            expenses = expenses.filter(date__range=[start_date, end_date])
        except:
            pass

    # -------------------------
    # BASIC METRICS
    # -------------------------
    total_expenses = expenses.aggregate(total=Sum("amount"))["total"] or 0
    total_records = expenses.count()
    total_categories = expenses.values("category").distinct().count()
    
    # total_spending = current month only, not all time
    if date_range and " to " in date_range:
        # User applied a date filter → total spending = filtered expenses
        total_spending = total_expenses  # already filtered above
    else:
        # No filter → show current month spending
        today = timezone.now()
        total_spending = Expense.objects.filter(
            created_by=request.user,
            date__year=today.year,
            date__month=today.month
        ).aggregate(total=Sum("amount"))["total"] or 0

    # -------------------------
    # CATEGORY DATA
    # -------------------------
    category_data = expenses.values("category__name").annotate(total=Sum("amount"))
    category_labels = [item["category__name"] for item in category_data]
    category_values = [float(item["total"]) for item in category_data]

    # -------------------------
    # MONTHLY DATA
    # -------------------------
    monthly_data = (
        expenses.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    monthly_labels = [item["month"].strftime("%b %Y") for item in monthly_data]
    monthly_values = [float(item["total"]) for item in monthly_data]

    # -------------------------
    # BUDGET LOGIC — CURRENT MONTH
    # -------------------------
    today = timezone.now()

    # ✅ FIX 1: Get current month's expenses only
    total_spent = Expense.objects.filter(
        created_by=request.user,
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum("amount"))["total"] or 0

    # ✅ FIX 2: Get current month's budget specifically
    budget = Budget.objects.filter(
        created_by=request.user,
        month__year=today.year,
        month__month=today.month
    ).first()

    budget_message = None
    budget_level = None
    budget_percent = 0

    if budget and budget.budget_limit:

        limit = float(budget.budget_limit)
        budget_percent = (float(total_spent) / limit) * 100

        # -------------------------
        # ALERTS
        # -------------------------
        if budget_percent >= 100:
            budget_message = f"🚨 Budget exceeded! ({budget_percent:.0f}%)"
            budget_level = "danger"

            # ✅ FIX 3: Send email once per WEEK not every session
            last_sent = request.session.get("budget_alert_last_sent")
            should_send = True

            if last_sent:
                from datetime import datetime
                last_sent_dt = datetime.fromisoformat(last_sent)
                days_since = (datetime.now() - last_sent_dt).days
                if days_since < 7:
                    should_send = False

            if should_send and request.user.email:
                try:
                    send_mail(
                        "Budget Exceeded Alert 🚨",
                        f"Hi {request.user.username},\n\n"
                        f"You have exceeded your budget for "
                        f"{today.strftime('%B %Y')}.\n\n"   # ✅ FIX 4: correct month name
                        f"Month: {today.strftime('%B %Y')}\n"
                        f"Spent:  ${total_spent:.2f}\n"
                        f"Limit:  ${limit:.2f}\n"
                        f"Usage:  {budget_percent:.0f}%\n\n"
                        f"Please review your expenses.",
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=False
                    )
                    # Save timestamp of last sent
                    request.session["budget_alert_last_sent"] = datetime.now().isoformat()

                except Exception as e:
                    print("EMAIL ERROR:", str(e))

        elif budget_percent >= 80:
            budget_message = f"⚠️ {budget_percent:.0f}% of budget used"
            budget_level = "high"

        elif budget_percent >= 70:
            budget_message = f"⚠️ {budget_percent:.0f}% budget usage"
            budget_level = "medium"

        elif budget_percent >= 50:
            budget_message = f"ℹ️ {budget_percent:.0f}% of budget used"
            budget_level = "low"

    # -------------------------
    # CONTEXT
    # -------------------------
    context = {
        "total_expenses": total_expenses,
        "total_records": total_records,
        "total_categories": total_categories,
        "total_spending": total_spending,
        "selected_dates": date_range,
        "category_labels": json.dumps(category_labels),
        "category_data": json.dumps(category_values),
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_data": json.dumps(monthly_values),
        "budget_message": budget_message,
        "budget_level": budget_level,
        "budget_percent": round(budget_percent, 1),
        "total_spent": total_spent,
        "budget": budget,
    }

    return render(request, "dashboard.html", context)