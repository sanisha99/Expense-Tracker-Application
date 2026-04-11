from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from tablib import Dataset
from .models import Expense, Category, Budget, Receipt


class SafeCategoryWidget(ForeignKeyWidget):

    def clean(self, value, row=None, **kwargs):
        if not value:
            return None
        category = Category.objects.filter(name=value.strip()).first()
        if not category:
            category = Category.objects.create(
                name=value.strip(),
                subcategory=row.get("item", "")
            )
        return category


class UserFilteredResource(resources.ModelResource):
    def __init__(self, user=None, **kwargs):
        super().__init__(**kwargs)
        self.user = user


class ExpenseResource(UserFilteredResource):  # inherits UserFilteredResource

    category = Field(
        column_name="category",
        attribute="category",
        widget=SafeCategoryWidget(Category, "name")
    )

    class Meta:
        model = Expense
        import_id_fields = ()
        fields = ("date", "item", "category", "tax_rate", "tax_amount", "amount")

    def before_import(self, dataset, **kwargs):
        normalized_headers = []
        for header in dataset.headers:
            clean = header.replace("\ufeff", "").strip().lower().replace(" ", "_")
            normalized_headers.append(clean)
        dataset.headers = normalized_headers

        if "total_amount" in dataset.headers:
            new_headers = [h for h in dataset.headers if h != "total_amount"]
            new_dataset = Dataset()
            new_dataset.headers = new_headers
            for row in dataset.dict:
                row.pop("total_amount", None)
                new_row = [row.get(col) for col in new_headers]
                new_dataset.append(new_row)
            dataset._data = new_dataset._data
            dataset.headers = new_dataset.headers

    def before_import_row(self, row, **kwargs):
        category_name = row.get("category")
        item_name = row.get("item")
        if category_name:
            Category.objects.get_or_create(
                name=category_name.strip(),
                subcategory=(item_name.strip() if item_name else ""),
                created_by=self.user  #  assign user to category
            )

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        instance.created_by = self.user  

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        if row_result.object_id:
            Expense.objects.filter(pk=row_result.object_id).update(created_by=self.user)


class ReceiptResource(UserFilteredResource):

    class Meta:
        model = Receipt
        import_id_fields = ()
        fields = ("item", "total_amount", "tax_amount", "uploaded_by", "created_at")

    def before_import_row(self, row, **kwargs):
        item_name = row.get("item")
        if item_name:
            Category.objects.get_or_create(
                name="Receipt",
                subcategory=item_name.strip()
            )


class CategoryResource(UserFilteredResource):

    class Meta:
        model = Category
        import_id_fields = ()
        fields = ("name", "subcategory", "created_at")


class BudgetResource(UserFilteredResource):

    category = Field(
        column_name="category",
        attribute="category",
        widget=SafeCategoryWidget(Category, "name")
    )

    class Meta:
        model = Budget
        import_id_fields = ()
        fields = ("category", "limit_amount", "created_at")