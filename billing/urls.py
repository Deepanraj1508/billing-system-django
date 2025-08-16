from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('billing/', views.billing_page, name='billing'),
    path('api/product/<str:product_id>/', views.get_product_info, name='get_product_info'),
    path('api/search-products/', views.search_products, name='search_products'),
    path('api/generate-bill/', views.generate_bill, name='generate_bill'),
    path('api/update-drawer-realtime/', views.update_drawer_realtime, name='update_drawer_realtime'),
    path('history/', views.purchase_history, name='purchase_history'),
    path('purchase/<uuid:purchase_id>/', views.purchase_detail, name='purchase_detail'),
    
    # Product Management
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Denomination Management
    path('denominations/', views.denomination_list, name='denomination_list'),
    path('denominations/add/', views.denomination_create, name='denomination_create'),
    path('denominations/<int:pk>/edit/', views.denomination_edit, name='denomination_edit'),
    path('denominations/<int:pk>/delete/', views.denomination_delete, name='denomination_delete'),
]