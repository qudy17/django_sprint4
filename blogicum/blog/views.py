from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from blog.models import Post, Category, Comment
from django.contrib.auth import get_user_model
from blog.forms import ProfileEditForm, PostForm, CommentForm
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.db.models import Count

User = get_user_model()


def index(request):
    """View функция - лента записей."""
    template = 'blog/index.html'
    current_time = timezone.now()

    post_list = Post.objects.select_related(
        'category', 'location'
    ).filter(
        is_published=True,
        pub_date__lte=current_time,
        category__is_published=True
    ).annotate(comment_count=Count('comment')).order_by('-pub_date')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    """View функция - конкретная выбранная запись в ленте."""
    post = get_object_or_404(
        Post.objects.select_related('location', 'category', 'author'),
        pk=post_id
    )

    if post.author != request.user:
        current_time = timezone.now()
        if not (post.is_published 
                and post.pub_date <= current_time 
                and post.category.is_published):
            raise Http404("Post not found")

    comments = post.comment_set.all()
    form = CommentForm()

    template = 'blog/detail.html'
    context = {
        "post": post,
        "comments": comments,
        "form": form,
    }
    return render(request, template, context)


def category_posts(request, category_slug):
    """View функция - категория постов."""
    template = 'blog/category.html'
    current_time = timezone.now()

    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = Post.objects.select_related(
        'category', 'location'
    ).filter(
        category=category,
        is_published=True,
        pub_date__lte=current_time
    ).annotate(comment_count=Count('comment')).order_by('-pub_date')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "category": category,
        "page_obj": page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    """View функция - профиль пользователя."""
    template = 'blog/profile.html'

    profile = get_object_or_404(User, username=username)

    if request.user == profile:
        post_list = Post.objects.select_related(
            'category', 'location'
        ).filter(
            author=profile
        ).annotate(comment_count=Count('comment')).order_by('-pub_date')
    else:
        current_time = timezone.now()
        post_list = Post.objects.select_related(
            'category', 'location'
        ).filter(
            author=profile,
            is_published=True,
            pub_date__lte=current_time,
            category__is_published=True
        ).annotate(comment_count=Count('comment')).order_by('-pub_date')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "profile": profile,
        "page_obj": page_obj,
    }
    return render(request, template, context)


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileEditForm
    template_name = 'blog/user.html'

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.object.username})


@login_required
def create_post(request):
    """View функция - создание поста."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    template = 'blog/create.html'
    context = {'form': form}
    return render(request, template, context)


@login_required
def edit_post(request, post_id):
    """View функция - редактирование поста."""
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    template = 'blog/create.html'
    context = {'form': form}
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    """View функция - добавления комментария."""
    post = get_object_or_404(
        Post.objects.select_related('location', 'category', 'author'),
        pk=post_id
    )

    if post.author != request.user:
        current_time = timezone.now()
        if not (post.is_published 
                and post.pub_date <= current_time 
                and post.category.is_published):
            raise Http404("Post not found")

    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post_id)

    comments = post.comment_set.all()
    context = {
        "post": post,
        "comments": comments,
        "form": form,
    }
    return render(request, 'blog/detail.html', context)


@login_required
def edit_comment(request, post_id, comment_id):
    """View функция - редактирования комментария."""
    comment = get_object_or_404(Comment, pk=comment_id, post__pk=post_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    template = 'blog/comment.html'
    context = {'form': form, 'comment': comment}
    return render(request, template, context)


@login_required
def delete_post(request, post_id):
    """View функция - удаление поста."""
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    form = PostForm(instance=post)
    template = 'blog/create.html'
    context = {'form': form}
    return render(request, template, context)


@login_required
def delete_comment(request, post_id, comment_id):
    """View функция - удаление комментария."""
    comment = get_object_or_404(Comment, pk=comment_id, post__pk=post_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    template = 'blog/comment.html'
    context = {'comment': comment}
    return render(request, template, context)
