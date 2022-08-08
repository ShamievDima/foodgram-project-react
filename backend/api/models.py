from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import UniqueConstraint

User = get_user_model()


class Recipe(models.Model):
    """ Основная модель приложения, описывающая рецепты.

    Поля:
        name(str) - Название рецепта.
        author(int) - Автор рецепта.
        tags(int) - Тэги рецепта. Связь M2M с моделью Tag.
        ingredients(int) - Ингредиенты для приготовления.
                           Связь M2M с моделью AmountIngredient.
        pub_date(datetime) - Дата добавления рецепта.
        image(str) - Изображение рецепта.
        text(str) - Описание рецепта.ё
        cooking_time(int) - Время приготовления рецепта.
    """

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название',
        help_text='Введите название рецепта',
    )
    image = models.ImageField(
        verbose_name='Картинка',
        upload_to='recipes/',
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
        help_text='Введите описание рецепта',
    )
    ingredients = models.ManyToManyField(
        'AmountIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
        help_text='Выберите ингредиенты для рецепта',
    )
    tags = models.ManyToManyField(
        'Tag',
        related_name='recipes',
        verbose_name='Тег',
        help_text='Выберите подходящие теги для рецепта',
    )
    cooking_time = models.IntegerField(
        verbose_name='Время приготовления в минутах',
        validators=[MinValueValidator(
            1,
            'Время приготовления не может быть меньше одной минуты'
        )],
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации',
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return f'{self.name}. Автор: {self.author.username}'


class Tag(models.Model):
    """ Модель тэгов созданных рецептов.

    Поля:
        name(str) - Уникальное название тэга.
        color(str) - Уникальный цвет тэга в HEX-кодировке.
        slug(str) - Уникальное название тэга латинскими буквами.
    """

    name = models.CharField(
        verbose_name='Название',
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Введите название тэга',
    )
    color = models.CharField(
        max_length=7,
        verbose_name='Цветовой HEX-код',
        validators=[RegexValidator(regex=r'^#([A-Fa-f0-9]{6})$')],
        unique=True,
    )
    slug = models.SlugField(
        max_length=20,
        unique=True,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return f'{self.name} (цвет: {self.color})'


class Ingredient(models.Model):
    """ Модель ингредиентов для рецептов.

        Поля:
        name(str) - Уникальное название ингредиента.
        measurement_unit(str) - Единицы измерения ингредента.
    """

    name = models.CharField(
        max_length=200,
        verbose_name='Название',
        help_text='Введите название ингредиента',
    )
    measurement_unit = models.CharField(
        max_length=200,
        verbose_name='Единица измерения',
        help_text='Введите единицу измерения',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class AmountIngredient(models.Model):
    """ Количество ингредиентов в блюде."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиенты',
        related_name='ingredient',
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество ингредиента',
        default=0,
        validators=(
            MinValueValidator(
                1, 'Слишком малое количество ингредиента.'
            ),
        ),
    )

    class Meta:
        verbose_name = 'Количество ингредиента'
        verbose_name_plural = 'Количество ингредиентов'
        constraints = (
            UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_ingredient',
            ),
        )

    def __str__(self):
        return f'{self.amount} {self.ingredient}'


class Favorite(models.Model):
    """ Модель для избранных рецептов"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_subscriber',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorite_recipe',
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = (
            UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite_recipe',
            ),
        )

    def __str__(self):
        return f'Рецепт {self.recipe} в избранном у {self.user}'


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
    )
    subscription_date = models.DateField(
        auto_now_add=True,
        verbose_name='Дата подписки',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            UniqueConstraint(
                fields=('user', 'author'),
                name='unique_for_author',
            ),
        )

    def __str__(self):
        return f'{self.user} подписан на {self.author}'


class Purchase(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='purchases',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='purchases',
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления',
    )

    class Meta:
        ordering = ('-date_added',)
        verbose_name = 'Покупка'
        verbose_name_plural = 'Покупки'
        constraints = (
            UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_purchase',
            ),
        )

    def __str__(self):
        return f'Рецепт {self.recipe} в списке покупок {self.user}'
