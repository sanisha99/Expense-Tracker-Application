from django.shortcuts import render
from django.core.paginator import Paginator
from apps.expenses.models import Category
from django.db.models import Q

def apply_category_search(queryset, request):

    search = request.GET.get("search")

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(subcategory__icontains=search)
        )

    return queryset


def categories_list(request):

    categories = Category.objects.all()
    #  SEARCH
    categories = apply_category_search(categories, request)
    # PAGINATION
    paginator = Paginator(categories, 5)   # 5 rows per page
    page_number = request.GET.get("page")

    categories = paginator.get_page(page_number)

    return render(request, "categories_list.html", {
        "categories": categories
    })