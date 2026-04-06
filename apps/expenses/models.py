from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Category(models.Model):

    name = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)

    def __str__(self):
        if self.subcategory:
            return f"{self.name} - {self.subcategory}"
        return self.name


class Expense(models.Model):

    date = models.DateField()

    item = models.CharField(max_length=200, blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="expenses_created"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item} - ${self.amount}"
    
class Budget(models.Model):

    month = models.DateField()

    total_income = models.DecimalField(max_digits=10, decimal_places=2)

    budget_limit = models.DecimalField(max_digits=10, decimal_places=2)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Prevent duplicate month (same year + month)
        existing = Budget.objects.filter(
            month__year=self.month.year,
            month__month=self.month.month
        )

        if self.pk:
            existing = existing.exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError("Budget for this month already exists.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Budget for {self.month}"

class Receipt(models.Model):

    image = models.ImageField(upload_to="receipts/")

    item = models.CharField(max_length=255)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.id}"