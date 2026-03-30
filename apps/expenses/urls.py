from django.urls import path

from .views.dashboard_view import dashboard
from .views.expense_view import expenses_list
from .views.category_view import categories_list
from .views.budget_view import budgets_list
from .views.receipt_view import receipts_list, generate_qr, mobile_upload
from .views.export_view import export_data
from .chatbot import chatbot_view


urlpatterns = [
    path("", dashboard),

    path("expenses/", expenses_list),
    path("categories/", categories_list),
    path("budgets/", budgets_list),
    path("receipts/", receipts_list),

    path("qr-code/", generate_qr, name="qr_code"),
    path("mobile-upload/", mobile_upload, name="mobile_upload"),

    path("export/<str:model_name>/", export_data, name="export_data"),
    path("chatbot/", chatbot_view, name="chatbot"),
]