from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def send_invite_email(user, request):
    """Generate a secure invite token and send welcome email."""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Build invite link
    invite_link = request.build_absolute_uri(
        f"/invite/set-password/{uid}/{token}/"
    )

    send_mail(
        subject="Welcome to Expense Tracker — Set Your Password",
        message=(
            f"Hi {user.username},\n\n"
            f"You have been invited to Expense Tracker.\n\n"
            f"Click the link below to set your password and get started:\n"
            f"{invite_link}\n\n"
            f"This link will expire after use.\n\n"
            f"If you did not expect this email, please ignore it."
        ),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False
    )


def set_password_view(request, uidb64, token):
    """Handle the invite link — let user set their password."""
    error = None
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Validate token
    if not user or not default_token_generator.check_token(user, token):
        return render(request, "invite_invalid.html")

    if request.method == "POST":
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not password1 or not password2:
            error = "Both fields are required."

        elif password1 != password2:
            error = "Passwords do not match."

        else:
            try:
                validate_password(password1, user)
                user.set_password(password1)
                user.save()

                # Auto login after setting password
                login(request, user)
                return redirect("/")

            except ValidationError as e:
                error = " ".join(e.messages)

    return render(request, "set_password.html", {
        "username": user.username,
        "error": error,
        "uidb64": uidb64,
        "token": token
    })