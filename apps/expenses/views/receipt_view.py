from apps.expenses.models import Receipt, Category
from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import HttpResponse
import cv2
import numpy as np
from import_export.formats import base_formats

from apps.expenses.services.receipt_scanner import scan_receipt
import qrcode

import pytesseract
import re
from PIL import Image
from tablib import Dataset

from apps.expenses.resources import ReceiptResource
from django.conf import settings
import os


def apply_receipt_search(queryset, request):
    """
    Search receipts by item
    """

    search = request.GET.get("search")

    if search:
        queryset = queryset.filter(item__icontains=search.strip())

    return queryset


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

    receipts = apply_receipt_search(receipts, request)

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