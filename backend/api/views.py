from datetime import timezone
import io

from django.http.response import HttpResponse, FileResponse
from django.db.models import Sum, F
from djoser.views import UserViewSet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST

from .filters import IngredientNameFilter, RecipeFilter
from .models import (Favorite, Follow, Ingredient, AmountIngredient,
                     Purchase, Recipe, Tag, User)
from .paginators import CustomPagination
from .permissions import IsOwnerOrAdminOrReadOnly
from .serializers import (FavoritesSerializer, ListRecipeSerializer,
                          IngredientSerializer, PurchaseSerializer,
                          CreateUpdateRecipeSerializer, ShowFollowerSerializer,
                          TagSerializer, UserSerializer)


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = CustomPagination
    serializer_class = UserSerializer
    permission_classes = (IsOwnerOrAdminOrReadOnly,)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)
        if user == author:
            return Response({
                'errors': 'Вы не можете подписываться на самого себя.'
            }, status=status.HTTP_400_BAD_REQUEST)
        if Follow.objects.filter(user=user, author=author).exists():
            return Response({
                'errors': 'Вы уже подписаны на данного пользователя.'
            }, status=status.HTTP_400_BAD_REQUEST)
        follow = Follow.objects.create(user=user, author=author)
        serializer = ShowFollowerSerializer(
            follow, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)
        subscribe = get_object_or_404(
            Follow, user=user, author=author
        )
        subscribe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = Follow.objects.filter(user=user)
        pages = self.paginate_queryset(queryset)
        serializer = ShowFollowerSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientsViewSet(viewsets.ModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    pagination_class = None
    permission_classes = (AllowAny,)
    filterset_class = IngredientNameFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    permission_classes = (IsOwnerOrAdminOrReadOnly,)
    filter_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            return CreateUpdateRecipeSerializer
        return ListRecipeSerializer

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    def recipe_post_method(self, request, AnySerializer, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        data = {
            'user': user.id,
            'recipe': recipe.id,
        }
        serializer = AnySerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def recipe_delete_method(self, request, AnyModel, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        favorites = get_object_or_404(
            AnyModel, user=user, recipe=recipe
        )
        favorites.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.recipe_post_method(
                request, FavoritesSerializer, pk
            )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self.recipe_delete_method(
            request, Favorite, pk
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.recipe_post_method(
                request, PurchaseSerializer, pk
            )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.recipe_delete_method(
            request, Purchase, pk
        )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        queryset = self.get_queryset()
        cart_objects = Purchase.objects.filter(user=request.user)
        recipes = queryset.filter(purchases__in=cart_objects)
        ingredients = AmountIngredient.objects.filter(recipes__in=recipes)
        ing_types = Ingredient.objects.filter(
            ingredients_amount__in=ingredients
        ).annotate(total=Sum('ingredients_amount__amount'))

        lines = [f'{ing_type.name}, {ing_type.total}'
                 f' {ing_type.measurement_unit}' for ing_type in ing_types]
        filename = 'shopping_ingredients.txt'
        response_content = '\n'.join(lines)
        response = HttpResponse(response_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
