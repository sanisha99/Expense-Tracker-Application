from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from apps.expenses.models import Expense, Budget


def get_total_spending(user=None, category=None, month=None, year=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if category:
        qs = qs.filter(category__name__iexact=category)

    if month and year:
        qs = qs.filter(date__year=year, date__month=month)

    return qs.aggregate(total=Sum("amount"))["total"] or 0


def get_category_breakdown(user=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    return list(
        qs.values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:10]
    )


def get_item_breakdown(user=None, category=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if category:
        qs = qs.filter(category__name__iexact=category)

    qs = qs.exclude(item__isnull=True).exclude(item="")

    return list(
        qs.values("item").annotate(total=Sum("amount")).order_by("-total")[:10]
    )


def get_highest_expense(user=None, category=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if category:
        qs = qs.filter(category__name__iexact=category)

    return qs.order_by("-amount").first()


def get_budget_summary(user=None):
    today = timezone.now()

    qs = Expense.objects.filter(
        date__year=today.year,
        date__month=today.month
    )

    if user:
        qs = qs.filter(created_by=user)

    total_spent = qs.aggregate(total=Sum("amount"))["total"] or 0

    budget_qs = Budget.objects.filter(
        month__year=today.year,
        month__month=today.month
    )

    if user:
        budget_qs = budget_qs.filter(created_by=user)

    budget = budget_qs.first()

    if not budget:
        return None

    remaining = float(budget.budget_limit) - float(total_spent)

    return {
        "income": float(budget.total_income),
        "limit": float(budget.budget_limit),
        "spent": float(total_spent),
        "remaining": float(remaining)
    }


def get_latest_expense(user=None, category=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if category:
        qs = qs.filter(category__name__iexact=category)

    return qs.order_by("-date").first()


def get_monthly_spending(user=None, year=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if year:
        qs = qs.filter(date__year=year)

    return list(
        qs.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )


def get_category_spending(user=None, category=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if category:
        qs = qs.filter(category__name__iexact=category)

    return qs.aggregate(total=Sum("amount"))["total"] or 0


def get_top_items(user=None, category=None, limit=5):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if category:
        qs = qs.filter(category__name__iexact=category)

    qs = qs.exclude(item__isnull=True).exclude(item="")

    return list(
        qs.values("item")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:limit]
    )


def list_expenses(user=None, limit=10):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    return list(
        qs.order_by("-date")
        .values("item", "amount", "date")[:limit]
    )


def get_spending_by_date_range(user=None, start_date=None, end_date=None):
    qs = Expense.objects.all()

    if user:
        qs = qs.filter(created_by=user)

    if start_date and end_date:
        qs = qs.filter(date__range=[start_date, end_date])

    return qs.aggregate(total=Sum("amount"))["total"] or 0