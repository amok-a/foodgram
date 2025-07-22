from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet, TagViewSet, IngredientViewSet,
    RecipeViewSet, SubscriptionViewSet, UserCreateView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('users/', UserCreateView.as_view(), name='user-create'),
    path('users/subscriptions/',
         SubscriptionViewSet.as_view({'get': 'list'}),
         name='user-subscriptions'),
    path('users/<int:author_id>/subscribe/',
         SubscriptionViewSet.as_view({'post': 'create', 'delete': 'destroy'}),
         name='subscribe'),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
