from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import Http404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import UserChangeForm
from django.db.models import Count

from .models import Post, Category, Comment
from .forms import PostForm, CommentForm, RegistrationForm

User = get_user_model()

MAIN_PAGE_LIMIT = 5
PROFILE_PAGE_LIMIT = 10


def paginate_queryset(request, queryset, items_per_page):
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def get_published_posts():
    return (
        Post.objects
        .select_related('category', 'location', 'author')
        .filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )
        .annotate(comment_count=Count('comments'))
        .order_by('-pub_date')
    )


def index(request):
    post_list = get_published_posts()[:MAIN_PAGE_LIMIT]

    return render(request, 'blog/index.html', {
        'post_list': post_list,
        'page_obj': post_list,
    })


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = get_published_posts().filter(category=category)

    return render(request, 'blog/category.html', {
        'category': category,
        'post_list': post_list,
        'page_obj': post_list,
    })


def post_detail(request, id):
    post = get_object_or_404(
        Post.objects.select_related('category', 'location', 'author'),
        pk=id,
    )

    if request.user != post.author:
        if not (post.is_published and
                post.pub_date <= timezone.now() and
                post.category.is_published):
            raise Http404("Пост не найден или не опубликован")

    comments = post.comments.select_related('author').all()
    form = CommentForm()

    return render(request, 'blog/detail.html', {
        'post': post,
        'comments': comments,
        'form': form,
        'comment_count': comments.count()
    })


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)

    if request.user == profile_user:
        post_list = (
            Post.objects
            .filter(author=profile_user)
            .select_related('category', 'location')
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date')
        )
    else:
        post_list = (
            Post.objects
            .filter(
                author=profile_user,
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True,
            )
            .select_related('category', 'location')
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date')
        )

    page_obj = paginate_queryset(request, post_list, PROFILE_PAGE_LIMIT)

    return render(request, 'blog/profile.html', {
        'profile_user': profile_user,
        'page_obj': page_obj,
        'post_list': page_obj.object_list,
    })


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = PostForm()

    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, id):
    post = get_object_or_404(Post, pk=id)

    if request.user != post.author:
        return redirect('blog:post_detail', id=post.id)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', id=post.id)
    else:
        form = PostForm(instance=post)

    return render(request, 'blog/create.html', {'form': form})


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'id'

    def test_func(self):
        return self.request.user == self.get_object().author

    def get_success_url(self):
        return reverse('blog:profile', kwargs={
            'username': self.request.user.username
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_delete'] = True
        context['form'] = PostForm(instance=self.object)
        return context


@login_required
def add_comment(request, id):
    post = get_object_or_404(Post, pk=id)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()

    return redirect('blog:post_detail', id=id)


@login_required
def edit_comment(request, id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=id)

    if request.user != comment.author:
        return redirect('blog:post_detail', id=id)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', id=id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'blog/comment.html', {
        'form': form,
        'comment': comment
    })


@login_required
def delete_comment(request, id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=id)

    if request.user != comment.author:
        return redirect('blog:post_detail', id=id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', id=id)

    return render(request, 'blog/comment.html', {
        'comment': comment
    })


@login_required
def edit_profile(request, username):
    if request.user.username != username:
        return redirect('blog:profile', username=username)

    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=username)
    else:
        form = UserChangeForm(instance=request.user)
        if 'password' in form.fields:
            del form.fields['password']

    return render(request, 'blog/user.html', {'form': form})


class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')
