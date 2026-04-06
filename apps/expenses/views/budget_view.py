from django.shortcuts import redirect, render
from django.core.paginator import Paginator
from apps.expenses.models import Budget

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import date
import calendar
import json
from django.contrib.auth.decorators import login_required


def apply_budget_filters(queryset, request):
    # FILTER BY USER 
    if request.user.is_authenticated:
        queryset = queryset.filter(created_by=request.user)

    start_month = request.GET.get("start_month")
    end_month = request.GET.get("end_month")

    error = None

    try:
        start_date = None
        end_date = None

        if start_month:
            y, m = map(int, start_month.split("-"))
            start_date = date(y, m, 1)

        if end_month:
            y, m = map(int, end_month.split("-"))
            last_day = calendar.monthrange(y, m)[1]
            end_date = date(y, m, last_day)

        # 🔴 VALIDATION CHECK
        if start_date and end_date and start_date > end_date:
            error = "Start month must be before end month"
            return queryset.none(), error

        if start_date:
            queryset = queryset.filter(month__gte=start_date)

        if end_date:
            queryset = queryset.filter(month__lte=end_date)

    except Exception as e:
        print("FILTER ERROR:", str(e))

    return queryset, error



@login_required
@require_http_methods(["POST"])
def edit_budget(request, budget_id):
    budget = get_object_or_404(Budget, id=budget_id, created_by=request.user)

    try:
        data = json.loads(request.body)
        month = data.get("month", "").strip()
        total_income = data.get("total_income")
        budget_limit = data.get("budget_limit")

        if not month or total_income is None or budget_limit is None:
            return JsonResponse({"success": False, "error": "All fields are required."})

        y, m = map(int, month.split("-"))
        month_date = date(y, m, 1)

        # Check duplicate excluding current
        exists = Budget.objects.filter(
            month=month_date,
            created_by=request.user
        ).exclude(id=budget_id).exists()

        if exists:
            return JsonResponse({"success": False, "error": f"A budget for {month} already exists."})

        budget.month = month_date
        budget.total_income = float(total_income)
        budget.budget_limit = float(budget_limit)
        budget.save()

        return JsonResponse({"success": True, "month": str(budget.month)})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_http_methods(["POST"])
def delete_budget(request, budget_id):
    budget = get_object_or_404(Budget, id=budget_id, created_by=request.user)
    try:
        budget.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@login_required
def budgets_list(request):

    # STEP 1: BASE QUERY
    budgets = Budget.objects.all().order_by("-month")

    # STEP 2: APPLY FILTER
    budgets, error = apply_budget_filters(budgets, request)

    # STEP 3: PAGINATION
    paginator = Paginator(budgets, 5)   
    page_number = request.GET.get("page")
    budgets = paginator.get_page(page_number)

    # STEP 4: CONTEXT
    context = {
        "budgets": budgets,
        "error": error
    }

    return render(request, "budgets_list.html", context)


@login_required
def add_budget(request):
    error = None

    if request.method == "POST":
        month = request.POST.get("month", "").strip()
        total_income = request.POST.get("total_income", "").strip()
        budget_limit = request.POST.get("budget_limit", "").strip()

        if not month or not total_income or not budget_limit:
            error = "All fields are required."
        else:
            try:
                # Convert "2026-04" → "2026-04-01" (first day of month)
                y, m = map(int, month.split("-"))
                month_date = date(y, m, 1)

                # Check duplicate
                exists = Budget.objects.filter(
                    month=month_date,
                    created_by=request.user
                ).exists()

                if exists:
                    error = f"A budget for {month} already exists."
                else:
                    Budget.objects.create(
                        month=month_date,        # ← proper date object
                        total_income=float(total_income),
                        budget_limit=float(budget_limit),
                        created_by=request.user
                    )
                    return redirect("/budgets/")

            except Exception as e:
                error = f"Error saving budget: {str(e)}"

    return render(request, "add_budget.html", {"error": error})
