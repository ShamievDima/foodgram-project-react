from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from .models import (Favorite, Follow, Ingredient, AmountIngredient,
                     Purchase, Recipe, Tag, User)


class UserSerializer(serializers.ModelSerializer):
    """ Сериализатор для модели User."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'password',
        )
        extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = 'is_subscribed',

    def get_is_subscribed(self, obj):
        """ Проверка подписки пользователя"""

        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Follow.objects.filter(
            user=request.user,
            author=obj.id).exists()

    def create(self, validated_data):
        """ Создание нового пользователя."""
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def validate_username(self, username):
        """ Проверяет введённый юзернейм."""
        if len(username) < 3:
            raise serializers.ValidationError(
                'Длина username допустима от '
                f'{3} до {150} букв'
            )
        if not username.isalpha():
            raise serializers.ValidationError(
                'В username допустимы только буквы.'
            )
        return username.capitalize()


class TagSerializer(serializers.ModelSerializer):
    """ Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientsAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = AmountIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class ListRecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор для получения списка рецептов"""

    image = Base64ImageField(max_length=None, use_url=True)
    tags = TagSerializer(read_only=True, many=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientsAmountSerializer(
        many=True,
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')
        read_only_fields = ('author', 'tags',)

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user,
                                           recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return Purchase.objects.filter(user=request.user,
                                           recipe=obj).exists()
        return False


class CreateUpdateRecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания и обновления рецептов"""

    image = Base64ImageField(max_length=None, use_url=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientsAmountSerializer(many=True)
    tags = TagSerializer(read_only=True, many=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def unique_item(self, items, Model):
         item_list = []
         for item in items:
             append_item = get_object_or_404(Model,
                                             id=item['id'])
             if append_item in item_list:
                 raise serializers.ValidationError('Элемент должен '
                                                   'быть уникальным')
             item_list.append(append_item)


    def validate(self, data):
        ingredients = data['ingredients']
        tags = data['tags']
        self.unique_item(ingredients, Ingredient)
        self.unique_item(tags, Tag)
        if not tags:
            raise serializers.ValidationError(
                'Укажите тэг для рецепта!')
        for tag_item in tags:
            if not Tag.objects.filter(name=tag_item).exists():
                raise serializers.ValidationError(
                    f'Тэга {tag_item} не существует!')
        data['tags'] = tags
        data['ingredients'] = ingredients
        return data

    def create_ingredients(self, ingredients, recipe):
        bulk_list = ()
        for ingredient in ingredients:
            bulk_list.append(
                AmountIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount'),
                )
            )
        AmountIngredient.objects.bulk_create(bulk_list)

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        image = validated_data.pop('image')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(image=image, **validated_data)
        self.create_ingredients(ingredients, recipe)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)
        if 'tags' in validated_data:
            instance.tags.set(
                validated_data.pop('tags'))
        return super().update(
            instance, validated_data)


class FollowerRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShowFollowerSerializer(serializers.ModelSerializer):
    """ Сериализатор для вывода авторов на которых подписан текущий пользователь."""

    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(
            user=obj.user, author=obj.author
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.author)
        if limit:
            queryset = queryset[:int(limit)]
        return FollowerRecipeSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()


class FavoritesSerializer(serializers.ModelSerializer):
    """ Сериализатор избранных рецептов"""

    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = Base64ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = Favorite
        fields = ('id', 'name', 'image', 'cooking_time', 'user', 'recipe')
        extra_kwargs = {'user': {'write_only': True},
                        'recipe': {'write_only': True}}

    def validate(self, data):
        if Favorite.objects.filter(user=data['user'],
                                   recipe=data['recipe']).exists():
            raise serializers.ValidationError(
                'Рецепт уже добавлен в избранное.'
            )
        return data


class PurchaseSerializer(FavoritesSerializer):
    """ Сериализатор списка покупок"""

    class Meta(FavoritesSerializer.Meta):
        model = Purchase

    def validate(self, data):
        request = self.context.get('request')
        recipe_id = data['recipe'].id
        purchase_exists = Purchase.objects.filter(
            user=request.user,
            recipe__id=recipe_id
        ).exists()

        if purchase_exists:
            raise serializers.ValidationError(
                'В списке покупок такой рецепт есть'
            )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return FollowerRecipeSerializer(
            instance.recipe,
            context=context).data
