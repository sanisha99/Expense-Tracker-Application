from apps.expenses.models import Expense, Category, Budget, Receipt
from tablib import Dataset
from import_export.formats import base_formats
from django.shortcuts import render

from apps.expenses.resources import ExpenseResource
from django.core.paginator import Paginator

def apply_expense_filters(queryset, request):
    """
    Reusable filter logic for expenses
    """

    # CATEGORY FILTER
    category = request.GET.get("category")

    if category:
        queryset = queryset.filter(
            category__name__iexact=category.strip()
        )

    return queryset

def expenses_list(request):

    expenses = Expense.objects.select_related("category").all()
    categories = Category.objects.values_list("name", flat=True).distinct()
    message = None

    if request.method == "POST":

        upload_file = request.FILES.get("import_file")

        if not upload_file:
            message = "No file selected."

        else:
            try:

                dataset = Dataset()
                file_name = upload_file.name.lower()

                if file_name.endswith(".csv"):
                    data = upload_file.read().decode("utf-8-sig")
                    dataset.load(data, format="csv")

                elif file_name.endswith(".tsv"):
                    data = upload_file.read().decode("utf-8-sig")
                    dataset.load(data, format="tsv")

                elif file_name.endswith(".json"):
                    data = upload_file.read().decode("utf-8")
                    dataset.load(data, format="json")

                elif file_name.endswith(".yaml"):
                    data = upload_file.read().decode("utf-8")
                    dataset.load(data, format="yaml")

                elif file_name.endswith(".html"):
                    data = upload_file.read().decode("utf-8")
                    dataset.load(data, format="html")

                elif file_name.endswith(".xlsx"):
                    dataset = base_formats.XLSX().create_dataset(upload_file.read())

                elif file_name.endswith(".xls"):
                    dataset = base_formats.XLS().create_dataset(upload_file.read())

                else:
                    message = "Unsupported file format."
                    return render(request, "expenses_list.html", {
                        "expenses": expenses,
                        "categories": categories,
                        "message": message
                    })

                resource = ExpenseResource()

                result = resource.import_data(dataset, dry_run=False)

                if result.has_errors():

                    error_list = []

                    # Row level errors
                    for row in result.row_errors():
                        error_list.append(str(row))

                    # Base errors (very important)
                    for error in result.base_errors:
                        error_list.append(str(error.error))

                    message = "Import error: " + ", ".join(error_list)

                elif result.has_validation_errors():

                    error_list = []

                    for row in result.invalid_rows:
                        error_list.append(str(row.error))

                    message = "Validation error: " + ", ".join(error_list)

                else:
                    message = "Expenses imported successfully."

            except Exception as e:
                message = f"Import failed: {str(e)}"

    expenses = apply_expense_filters(expenses, request)

    paginator = Paginator(expenses, 10)
    page_number = request.GET.get("page")
    expenses = paginator.get_page(page_number)

    return render(request, "expenses_list.html", {
        "expenses": expenses,
        "categories": categories,
        "message": message
    })
