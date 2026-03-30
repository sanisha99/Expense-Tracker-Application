import pytesseract
from PIL import Image
import re


def scan_receipt(image_path):

    image = Image.open(image_path)

    text = pytesseract.image_to_string(image)

    item = None
    total = None
    tax = None

    # Extract item
    item_match = re.search(r"Item:\s*(.*)", text)
    if item_match:
        item = item_match.group(1).strip()

    # Extract total amount
    total_match = re.search(r"Total:\s*\$?(\d+\.\d+)", text)
    if total_match:
        total = total_match.group(1)

    # Extract tax
    tax_match = re.search(r"Tax:\s*\$?(\d+\.\d+)", text)
    if tax_match:
        tax = tax_match.group(1)

    total = float(total) if total else 0
    tax = float(tax) if tax else 0

    return {
        "item": item,
        "total": total,
        "tax": tax
    }