from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from apps.expenses.models import Expense, Budget


def get_total_spending(category=None, month=None, year=None):
    qs = Expense.objects.all()

    if category:
        qs = qs.filter(category__name__iexact=category)

    if month and year:
        qs = qs.filter(date__year=year, date__month=month)

    return qs.aggregate(total=Sum("amount"))["total"] or 0


def get_category_breakdown():
    return list(
        Expense.objects
        .values("category__name")
        .annotate(total=Sum("amount"))
    )


def get_item_breakdown(category=None):
    qs = Expense.objects.all()

    if category:
        qs = qs.filter(category__name__iexact=category)

    qs = qs.exclude(item__isnull=True).exclude(item="")

    return list(
        qs.values("item").annotate(total=Sum("amount"))
    )


def get_highest_expense(category=None):
    qs = Expense.objects.all()

    if category:
        qs = qs.filter(category__name__iexact=category)

    return qs.order_by("-amount").first()


def get_budget_summary():
    today = timezone.now()

    total_spent = Expense.objects.filter(
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum("amount"))["total"] or 0

    budget = Budget.objects.filter(
        month__year=today.year,
        month__month=today.month
    ).first()

    if not budget:
        return None

    remaining = float(budget.budget_limit) - float(total_spent)

    return {
        "income": float(budget.total_income),
        "limit": float(budget.budget_limit),
        "spent": float(total_spent),
        "remaining": float(remaining)
    }