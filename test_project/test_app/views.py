from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView


def test_menus(request):
    return render(request, 'test_menus.html', {})


@login_required
def test_login_required(request):
    return render(request, 'test_menus.html', {})


@user_passes_test(lambda user: user.is_staff)
def test_user_passes_test(request):
    return render(request, 'test_menus.html', {})


@permission_required('test_app.xxx')
def test_permission_required(request):
    return render(request, 'test_menus.html', {})


@staff_member_required
def test_staff_required(request):
    return render(request, 'test_menus.html', {})


class TestCBV(TemplateView):
    template_name = 'test_menus.html'

    @method_decorator(login_required)
    def get(self, *args, **kwargs):
        return super(TestCBV, self).get(*args, **kwargs)
