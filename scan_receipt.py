import pytesseract
from PIL import Image

# Path to receipt image
image_path = "sample_receipt.jpg"

# Open image
image = Image.open(image_path)

# Run OCR
text = pytesseract.image_to_string(image)

# Print extracted text
print("OCR RESULT:")
print("----------------")
print(text)