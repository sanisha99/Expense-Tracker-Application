from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from apps.expenses.models import Expense, Category, Budget, Receipt


def send_invite(user, request):
    from apps.expenses.views.invite_user_view import send_invite_email
    send_invite_email(user, request)


class CustomUserAdmin(UserAdmin):

    def save_model(self, request, obj, form, change):
        # Capture old email BEFORE saving
        old_email = None
        if change and obj.pk:
            try:
                old_email = User.objects.get(pk=obj.pk).email
            except User.DoesNotExist:
                pass

        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        new_email = obj.email

        # Send invite if:
        # 1. Brand new user with email already filled
        # 2. Existing user who just got an email added for the first time
        
        should_send = (
            (is_new and new_email) or
            (change and new_email and not old_email)
        )

        if should_send:
            try:
                send_invite(obj, request)
                self.message_user(
                    request,
                    f"✅ Invite email sent to {new_email}"
                )
                print(f"INVITE EMAIL SENT TO: {new_email}")
            except Exception as e:
                self.message_user(
                    request,
                    f"❌ User created but email failed: {str(e)}"
                )
                print(f"INVITE EMAIL ERROR: {str(e)}")

# Unregister default User and register with CustomUserAdmin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)


# Register your models
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["item", "amount", "category", "date", "created_by"]
    list_filter = ["category", "date"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "subcategory", "created_by"]


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["month", "total_income", "budget_limit", "created_by"]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["item", "total_amount", "created_at"]