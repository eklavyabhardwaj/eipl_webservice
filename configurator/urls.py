# configurator/urls.py
from django.urls import path
from .views import (
    GroupListView, QuizView, PageView, product_menu_api,
    CareerListView, CareerDetailView, CareerApplyView, CareerTermsView,
    ContactView, contact_thanks,
    GroupExploreView, ItemDetailView,   # <-- add these two imports
)

app_name = "configurator"

urlpatterns = [
    path("", PageView.as_view(), name="home"),
    path("pages/<slug:slug>/", PageView.as_view(), name="page"),
    path("quiz/", GroupListView.as_view(), name="group_list"),
    path("quiz/<slug:slug>/", QuizView.as_view(), name="quiz"),

    # NEW:
    path("quiz/<slug:slug>/explore/", GroupExploreView.as_view(), name="group_explore"),
    path("item/<int:item_id>/", ItemDetailView.as_view(), name="item_detail"),

    path("api/product-menu/", product_menu_api, name="product_menu_api"),
    path("careers/", CareerListView.as_view(), name="career_list"),
    path("careers/job/<str:job_id>/", CareerDetailView.as_view(), name="career_detail"),
    path("careers/apply/", CareerApplyView.as_view(), name="career_apply"),
    path("careers/terms/", CareerTermsView.as_view(), name="career_terms"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("contact/thanks/", contact_thanks, name="contact_thanks"),
]
