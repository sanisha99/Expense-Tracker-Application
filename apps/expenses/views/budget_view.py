from django.shortcuts import render
from django.core.paginator import Paginator
from apps.expenses.models import Budget


def apply_budget_filters(queryset, request):
    """
    Filter budgets by month range
    """

    start_month = request.GET.get("start_month")
    end_month = request.GET.get("end_month")

    if start_month and end_month:
        try:
            start_year, start_m = start_month.split("-")
            end_year, end_m = end_month.split("-")

            queryset = queryset.filter(
                month__gte=f"{start_year}-{start_m}-01",
                month__lte=f"{end_year}-{end_m}-31"
            )
        except:
            pass
    if start_month:
        queryset = queryset.filter(month__gte=f"{start_month}-01")

    if end_month:
        queryset = queryset.filter(month__lte=f"{end_month}-31")

    return queryset


def budgets_list(request):

    # STEP 1: BASE QUERY
    budgets = Budget.objects.all()

    # STEP 2: APPLY FILTER
    budgets = apply_budget_filters(budgets, request)

    # STEP 3: PAGINATION
    paginator = Paginator(budgets, 5)   # 5 per page (you can change)
    page_number = request.GET.get("page")
    budgets = paginator.get_page(page_number)

    # STEP 4: CONTEXT
    context = {
        "budgets": budgets
    }

    return render(request, "budgets_list.html", context)
