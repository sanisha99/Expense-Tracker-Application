from apps.expenses.models import Expense, Category, Budget, Receipt
from tablib import Dataset
from import_export.formats import base_formats
from django.shortcuts import redirect, render

from apps.expenses.resources import ExpenseResource
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
import json


def apply_expense_filters(queryset, request):
    """
    Reusable filter logic for expenses
    """
    #  FILTER BY USER (VERY IMPORTANT)
    if request.user.is_authenticated:
        queryset = queryset.filter(created_by=request.user)

    # CATEGORY FILTER
    category = request.GET.get("category")

    if category:
        queryset = queryset.filter(
            category__name__iexact=category.strip()
        )

    return queryset

@login_required
def add_expense(request):

    categories = Category.objects.filter(created_by=request.user)  # filter by user

    if request.method == "POST":

        item = request.POST.get("item")
        amount = request.POST.get("amount")
        date = request.POST.get("date")
        tax_rate = request.POST.get("tax_rate") or 0

        try:
            category_id = request.POST.get("category")
            
            # Step 1: Get the selected category to read its name
            selected_category = Category.objects.get(id=category_id, created_by=request.user)

            # Step 2: Get or create the name+subcategory pair only if it doesn't exist
            category, created = Category.objects.get_or_create(
                name=selected_category.name,
                subcategory=item,
                created_by=request.user
            )

            # Calculate tax
            tax_amount = (float(amount) * float(tax_rate)) / 100

            Expense.objects.create(
                item=item,
                amount=amount,
                category=category,
                date=date,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                created_by=request.user
            )

            return redirect('/expenses/')

        except Category.DoesNotExist:
            return render(request, "add_expense.html", {
                "categories": categories,
                "error": "Selected category not found."
            })
        except Exception as e:
            return render(request, "add_expense.html", {
                "categories": categories,
                "error": str(e)
            })

    return render(request, "add_expense.html", {
        "categories": categories
    })


@login_required
def expenses_list(request):

    expenses = Expense.objects.select_related("category").all()
    categories = Category.objects.filter(created_by=request.user).values_list("name", flat=True).distinct()

    categories_obj = Category.objects.filter(created_by=request.user).values("id", "name").distinct()

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

                resource = ExpenseResource(user=request.user)
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
        "categories_obj": list(categories_obj),
        "message": message
    })


@login_required
@require_http_methods(["POST"])
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, created_by=request.user)
    try:
        data = json.loads(request.body)
        item      = data.get("item", "").strip()
        amount    = data.get("amount")
        date_val  = data.get("date", "").strip()
        tax_rate  = data.get("tax_rate", 0)
        category_id = data.get("category_id")

        if not item or not amount or not date_val:
            return JsonResponse({"success": False, "error": "Item, amount and date are required."})

        category = get_object_or_404(Category, id=category_id, created_by=request.user)

        # Get or create the name+subcategory pair
        category, _ = Category.objects.get_or_create(
            name=category.name,
            subcategory=item,
            created_by=request.user
        )

        tax_amount = (float(amount) * float(tax_rate)) / 100

        expense.item       = item
        expense.amount     = float(amount)
        expense.date       = date_val
        expense.tax_rate   = float(tax_rate)
        expense.tax_amount = tax_amount
        expense.category   = category
        expense.save()

        return JsonResponse({
            "success": True,
            "item": expense.item,
            "amount": str(expense.amount),
            "date": str(expense.date),
            "tax_rate": str(expense.tax_rate),
            "tax_amount": str(expense.tax_amount),
            "category_name": expense.category.name,
            "category_id": expense.category.id
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_http_methods(["POST"])
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, created_by=request.user)
    try:
        expense.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})