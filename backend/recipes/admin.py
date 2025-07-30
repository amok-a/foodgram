from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
import json


from .models import (Tag, Ingredient, Recipe,
                     RecipeIngredient, Favorite, ShoppingCart, Subscription)
from users.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff",
                    "recipe_count", "subscriber_count")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (("Personal info"), {"fields": ("first_name", "last_name",
                                        "email", "avatar")}),
        (("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser",
                                      "groups", "user_permissions")}),
        (("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "password1", "password2",
                "email", "first_name", "last_name"),
        }),
    )
    readonly_fields = ("recipe_count", "subscriber_count")
    search_fields = ('username', 'email')


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [RecipeIngredientInline]
    list_display = ('name', 'author', 'cooking_time')
    filter_horizontal = ('tags',)
    fieldsets = (
        (None, {
            'fields': ('name', 'author', 'text', 'image', 'cooking_time')
        }),
        ('Теги', {
            'fields': ('tags',),
        }),
        ('Статистика', {
            'fields': ('favorite_count',),
        }),
    )

    @admin.display(description='В избранном')
    def favorite_count(self, obj):
        return obj.favorites.count()

    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    readonly_fields = ('favorite_count',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)

    def import_from_json(self, request, queryset):
        with open('data/ingredients.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                Ingredient.objects.get_or_create(
                    name=item['name'],
                    measurement_unit=item['measurement_unit']
                )
        self.message_user(request, "Ингредиенты успешно загружены")


admin.site.register(Tag)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(RecipeIngredient)
admin.site.register(Favorite)
admin.site.register(ShoppingCart)
admin.site.register(Subscription)
