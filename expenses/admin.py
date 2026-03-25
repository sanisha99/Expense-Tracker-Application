from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Expense, Category, Budget, Receipt
from .resources import ExpenseResource


class ExpenseAdmin(ImportExportModelAdmin):

    resource_class = ExpenseResource

    list_display = (
        'date',
        'item',
        'category',
        'tax_rate',
        'tax_amount',
        'amount',
        'created_by',
        'created_at'
    )

    search_fields = ('item', 'category__name')

    list_filter = ('category', 'date')

    # Auto-fill created_by and modified_by
    def save_model(self, request, obj, form, change):

        if not obj.created_by:
            obj.created_by = request.user

        obj.modified_by = request.user

        super().save_model(request, obj, form, change)


class CategoryAdmin(ImportExportModelAdmin):

    list_display = ('name', 'subcategory', 'created_at')

    search_fields = ('name', 'subcategory')


# NEW ADMIN CLASSES

class BudgetAdmin(ImportExportModelAdmin):

    list_display = (
        'month',
        'total_income',
        'budget_limit',
        'created_by',
        'created_at'
    )


class ReceiptAdmin(ImportExportModelAdmin):

    list_display = (
        'item',
        'total_amount',
        'tax_amount',
        'uploaded_by',
        'created_at'
    )


# REGISTER MODELS

admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Budget, BudgetAdmin)
admin.site.register(Receipt, ReceiptAdmin)