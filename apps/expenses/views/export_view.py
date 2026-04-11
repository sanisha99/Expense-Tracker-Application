from apps.expenses.resources import ExpenseResource, ReceiptResource, CategoryResource, BudgetResource
from django.http import HttpResponse
from apps.expenses.models import Expense, Category, Budget, Receipt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

@login_required
def export_data(request, model_name):
    user = request.user

    if model_name == "expenses":
        resource = ExpenseResource(user=request.user)
        queryset = Expense.objects.filter(created_by=user)
        filename = "expenses.csv"
    elif model_name == "receipts":
        resource = ReceiptResource(user=request.user)
        queryset = Receipt.objects.filter(created_by=user)
        filename = "receipts.csv"
    elif model_name == "categories":
        resource = CategoryResource(user=request.user)
        queryset = Category.objects.filter(created_by=user)
        filename = "categories.csv"
    elif model_name == "budgets":
        resource = BudgetResource(user=request.user)
        queryset = Budget.objects.filter(created_by=user)
        filename = "budgets.csv"
    else:
        return HttpResponse("Invalid export request.")
    
    if not queryset.exists():
        messages.error(request, f"No {model_name} data found to export.")
        return redirect(request.META.get("HTTP_REFERER", "/"))


    dataset = resource.export(queryset)  # filtered queryset passed directly

    response = HttpResponse(dataset.csv, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response