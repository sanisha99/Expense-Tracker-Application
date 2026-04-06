from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from apps.expenses.models import Category
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

def apply_category_search(queryset, request):

    search = request.GET.get("search")

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(subcategory__icontains=search)
        )

    return queryset

@login_required
def categories_list(request):

    categories = Category.objects.filter(created_by=request.user)
    #  SEARCH
    categories = apply_category_search(categories, request)
    # PAGINATION
    paginator = Paginator(categories, 5)   # 5 rows per page
    page_number = request.GET.get("page")

    categories = paginator.get_page(page_number)

    return render(request, "categories_list.html", {
        "categories": categories
    })

@login_required
def add_category(request):
    error = None

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        subcategory = request.POST.get("subcategory", "").strip()

        if not name or not subcategory:
            error = "Both Category Name and Subcategory are required."
        else:
            # Only create if this exact pair doesn't already exist
            exists = Category.objects.filter(
                name__iexact=name,
                subcategory__iexact=subcategory,
                created_by=request.user
            ).exists()

            if exists:
                error = f'"{name} → {subcategory}" already exists.'
            else:
                Category.objects.create(
                    name=name,
                    subcategory=subcategory,
                    created_by=request.user
                )
                return redirect("/categories/")

    return render(request, "add_category.html", {"error": error})


@login_required
@require_http_methods(["POST"])
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id, created_by=request.user)
    try:
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        subcategory = data.get("subcategory", "").strip()

        if not name or not subcategory:
            return JsonResponse({"success": False, "error": "Both fields are required."})

        # Check duplicate excluding current
        exists = Category.objects.filter(
            name__iexact=name,
            subcategory__iexact=subcategory,
            created_by=request.user
        ).exclude(id=category_id).exists()

        if exists:
            return JsonResponse({"success": False, "error": f'"{name} → {subcategory}" already exists.'})

        category.name = name
        category.subcategory = subcategory
        category.save()

        return JsonResponse({"success": True, "name": category.name, "subcategory": category.subcategory})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_http_methods(["POST"])
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id, created_by=request.user)
    try:
        category.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
