from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User
from .utils import paginate_page


def index(request):
    post_list = Post.objects.all()
    context = {
        "page_obj": paginate_page(request, post_list),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.group.all()
    context = {
        "group": group,
        "page_obj": paginate_page(request, post_list),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author_id = get_object_or_404(User, username=username)
    post_list = author_id.posts.all()
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user, author=author_id
        ).exists()
    else:
        following = False
    context = {
        "page_obj": paginate_page(request, post_list),
        "author_id": author_id,
        "post_list": post_list,
        "following": following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()
    comments = post.comments.all()
    context = {
        "post": post,
        "form": form,
        "comments": comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user.username)
    context = {
        "form": form,
        "is_edit": False,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post.pk)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post.pk)
    context = {
        "form": form,
        "is_edit": True,
        "post": post,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        "form": form,
        "post": post,
    }
    return render(request, 'includes/comment.html', context)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    context = {
        "page_obj": paginate_page(request, post_list)
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = User.objects.get(username=username)
    follower = Follow.objects.filter(user=request.user, author=author)
    if request.user != author and not follower.exists():
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect(
        reverse('posts:profile', args=[username]),
    )


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    is_follower = Follow.objects.filter(user=request.user, author=author)
    if is_follower.exists():
        is_follower.delete()
    return redirect('posts:profile', username=author)
