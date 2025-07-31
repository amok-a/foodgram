from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet, TagViewSet, IngredientViewSet,
    RecipeViewSet, UserCreateView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('users/', UserCreateView.as_view(), name='user-create'),
    path('users/subscriptions/',
         UserViewSet.as_view({'get': 'subscriptions'}),
         name='user-subscriptions'),
    path('users/<int:pk>/subscribe/',
         UserViewSet.as_view({'post': 'subscribe', 'delete': 'subscribe'}),
         name='subscribe'),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
