from .models import Page

def menu_pages(request):
    return {
        "menu_pages": Page.objects.filter(is_active=True).order_by("menu_order")
    }
