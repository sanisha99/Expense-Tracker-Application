from django.urls import path

from .views.dashboard_view import dashboard
from .views.expense_view import expenses_list,add_expense,edit_expense,delete_expense
from .views.budget_view import budgets_list,add_budget,edit_budget,delete_budget
from .views.receipt_view import receipts_list, generate_qr, mobile_upload
from .views.export_view import export_data
from .chatbot import chatbot_view
from .views.category_view import categories_list, add_category,edit_category,delete_category
from apps.expenses.views.invite_user_view import set_password_view


urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("expenses/", expenses_list, name="expenses_list"),
    path("expenses/add/", add_expense, name="add_expense"),
    path("expenses/<int:expense_id>/edit/", edit_expense, name="edit_expense"),
    path("expenses/<int:expense_id>/delete/", delete_expense, name="delete_expense"),
    path("categories/", categories_list, name="categories_list"),
    path("categories/<int:category_id>/edit/", edit_category, name="edit_category"),
    path("categories/<int:category_id>/delete/", delete_category, name="delete_category"),
    path("categories/add/", add_category, name="add_category"),
    path("budgets/", budgets_list, name="budgets_list"),
    path("budgets/<int:budget_id>/edit/", edit_budget, name="edit_budget"),
    path("budgets/<int:budget_id>/delete/", delete_budget, name="delete_budget"),
    path("budgets/add/", add_budget, name="add_budget"), 
    path("receipts/", receipts_list,name="receipts_list"),

    path("qr-code/", generate_qr, name="qr_code"),
    path("mobile-upload/", mobile_upload, name="mobile_upload"),

    path("export/<str:model_name>/", export_data, name="export_data"),
    path("chatbot/", chatbot_view, name="chatbot"),
    path("invite/set-password/<uidb64>/<token>/", set_password_view, name="set_password"),
]