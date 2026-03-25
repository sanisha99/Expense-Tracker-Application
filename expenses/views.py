from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from tablib import Dataset
from import_export.formats import base_formats
from django.http import HttpResponse
from .models import Expense, Category, Budget, Receipt
from .resources import ExpenseResource, ReceiptResource, CategoryResource, BudgetResource
from .receipt_scanner import scan_receipt
import qrcode
from django.http import HttpResponse
from django.core.paginator import Paginator

import pytesseract
import re
from PIL import Image
from django.conf import settings
import os
from .models import Receipt
from django.utils import timezone

import cv2
import numpy as np

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

def expenses_list(request):

    expenses = Expense.objects.select_related("category").all()
    categories = Category.objects.all()
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

    category_filter = request.GET.get("category")

    if category_filter:
        expenses = expenses.filter(category__name=category_filter)

    paginator = Paginator(expenses, 10)
    page_number = request.GET.get("page")
    expenses = paginator.get_page(page_number)

    return render(request, "expenses_list.html", {
        "expenses": expenses,
        "categories": categories,
        "message": message
    })

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


def categories_list(request):

    categories_list = Category.objects.all()

    paginator = Paginator(categories_list, 5)   # 5 rows per page
    page_number = request.GET.get("page")

    categories = paginator.get_page(page_number)

    return render(request, "categories_list.html", {
        "categories": categories
    })


def budgets_list(request):

    budgets = Budget.objects.all()

    context = {
        "budgets": budgets
    }

    return render(request, "budgets_list.html", context)


def receipts_list(request):

    receipts = Receipt.objects.all().order_by("-created_at")
    message = None

    if request.method == "POST":

        try:

            # ==========================
            # 1️⃣ CSV / Excel IMPORT
            # ==========================
            import_file = request.FILES.get("import_file")

            if import_file:

                file_format = import_file.name.split(".")[-1].lower()

                format_map = {
                    "csv": base_formats.CSV(),
                    "xlsx": base_formats.XLSX(),
                    "xls": base_formats.XLS(),
                    "json": base_formats.JSON(),
                    "tsv": base_formats.TSV(),
                    "yaml": base_formats.YAML(),
                    "html": base_formats.HTML(),
                }

                if file_format not in format_map:
                    message = "Unsupported file format."

                else:

                    dataset = Dataset()

                    if file_format in ["csv", "tsv", "json", "yaml", "html"]:
                        data = import_file.read().decode("utf-8")
                        dataset.load(data, format=file_format)
                    else:
                        dataset = format_map[file_format].create_dataset(import_file.read())

                    resource = ReceiptResource()

                    result = resource.import_data(dataset, dry_run=False)

                    if result.has_errors() or result.has_validation_errors():

                        errors = []

                        for row in result.row_errors():
                            errors.append(str(row[1]))

                        for err in result.base_errors:
                            errors.append(str(err))

                        message = "Import failed: " + "; ".join(errors)

                    else:
                        message = "File imported successfully."

            # ==========================
            # 2️⃣ RECEIPT SCANNER
            # ==========================
            image = request.FILES.get("receipt_image")

            if image:

                temp_path = os.path.join(settings.MEDIA_ROOT, "sample_receipt.jpg")

                with open(temp_path, "wb+") as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)

                img = cv2.imread(temp_path)

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                blur = cv2.GaussianBlur(gray, (3,3), 0)

                text = pytesseract.image_to_string(blur)

                print("OCR TEXT:", text)

                prices = re.findall(r"\d+\.\d{2}", text)

                print("Detected prices:", prices)

                if not prices:
                    message = "Unable to detect receipt details. Please upload a clearer receipt."

                else:

                    prices = [float(p) for p in prices]

                    total_amount = max(prices)

                    tax_amount = 0
                    for p in prices:
                        if "tax" in text.lower() and p != total_amount:
                            tax_amount = p

                    item_name = "Scanned Receipt"

                    # 🔹 Update Category table
                    Category.objects.get_or_create(
                        name="Receipt",
                        subcategory=item_name
                    )

                    Receipt.objects.create(
                        image=image,
                        item=item_name,
                        total_amount=total_amount,
                        tax_amount=tax_amount,
                        uploaded_by=request.user if request.user.is_authenticated else None
                    )

                    message = "Receipt scanned and saved successfully."

        except Exception as e:

            print("ERROR:", e)

            message = "Something went wrong while processing the request."

    paginator = Paginator(receipts, 10)
    page_number = request.GET.get("page")
    receipts = paginator.get_page(page_number)

    return render(request, "receipts_list.html", {
        "receipts": receipts,
        "message": message
    })



def generate_qr(request):

    qr_data = "http://192.168.1.22:8000/mobile-upload/"

    qr = qrcode.make(qr_data)

    response = HttpResponse(content_type="image/png")
    qr.save(response, "PNG")

    return response

def mobile_upload(request):

    message = None

    if request.method == "POST":

        try:

            image_file = request.FILES.get("receipt_image")

            if not image_file:
                message = "Please upload a receipt image."
                return render(request, "mobile_upload.html", {"message": message})

            # Save uploaded image
            image_path = os.path.join(settings.MEDIA_ROOT, "sample_receipt.jpg")

            with open(image_path, "wb+") as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            # Load image using OpenCV
            img = cv2.imread(image_path)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

            blur = cv2.GaussianBlur(thresh, (5,5), 0)

            # Run OCR
            text = pytesseract.image_to_string(blur)

            print("OCR TEXT:", text)

            # Extract prices
            prices = re.findall(r"\d+\.\d{2}", text)

            print("Detected prices:", prices)

            if not prices:
                message = "Unable to detect receipt details. Please upload a clearer receipt."
                return render(request, "mobile_upload.html", {"message": message})

            prices = [float(p) for p in prices]

            # Largest value = total
            total_amount = max(prices)

            # Detect tax (look for values smaller than total)
            tax_amount = 0
            for p in prices:
                if "tax" in text.lower() and p != total_amount:
                    tax_amount = p

            # Save receipt
            Receipt.objects.create(
                image=image_file,
                item="Scanned Receipt",
                total_amount=total_amount,
                tax_amount=tax_amount,
                uploaded_by=request.user if request.user.is_authenticated else None
            )

            message = "Receipt scanned and saved successfully."

        except Exception as e:

            print("OCR ERROR:", e)

            message = "Something went wrong while scanning the receipt. Please try again."

    return render(request, "mobile_upload.html", {"message": message})