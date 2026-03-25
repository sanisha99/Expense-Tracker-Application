"""
URL configuration for expense_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from expenses import views
from django.conf import settings
from django.conf.urls.static import static
from expenses.chatbot import chatbot_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.dashboard),
    path("expenses/", views.expenses_list),
    path("categories/", views.categories_list),
    path("budgets/", views.budgets_list),
    path("receipts/", views.receipts_list),
    path("qr-code/", views.generate_qr,name="qr_code"),
    path("mobile-upload/", views.mobile_upload, name="mobile_upload"),
    path("export/<str:model_name>/", views.export_data, name="export_data"),
    path("chatbot/", chatbot_view, name="chatbot"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)