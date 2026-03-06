from django.contrib import admin
from .models import Category, Location, Post, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published')
    list_filter = ('is_published',)
    search_fields = ('title', 'description')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_published')
    list_filter = ('is_published',)
    search_fields = ('name',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'pub_date',
        'author',
        'category',
        'location',
        'is_published'
    )
    list_filter = ('category', 'location', 'is_published')
    list_editable = ('is_published',)
    search_fields = ('title', 'text')
    date_hierarchy = 'pub_date'
    raw_id_fields = ('author',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'author', 'post', 'created_at')
    list_filter = ('author', 'created_at')
    search_fields = ('text', 'author__username', 'post__title')
    raw_id_fields = ('author', 'post')
    readonly_fields = ('created_at',)

    def short_text(self, obj):
        if len(obj.text) > 50:
            return obj.text[:50] + '...'
        return obj.text
    short_text.short_description = 'Текст комментария'
