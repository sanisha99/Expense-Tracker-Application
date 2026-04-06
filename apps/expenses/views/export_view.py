from apps.expenses.resources import ExpenseResource, ReceiptResource, CategoryResource, BudgetResource
from django.http import HttpResponse


def export_data(request, model_name):

    if model_name == "expenses":
        resource = ExpenseResource()
        filename = "expenses.csv"

    elif model_name == "receipts":
        resource = ReceiptResource()
        filename = "receipts.csv"

    elif model_name == "categories":
        resource = CategoryResource()
        filename = "categories.csv"

    elif model_name == "budgets":
        resource = BudgetResource()
        filename = "budgets.csv"

    else:
        return HttpResponse("Invalid export request.")

    dataset = resource.export()

    response = HttpResponse(dataset.csv, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response
