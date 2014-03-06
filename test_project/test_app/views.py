from django.shortcuts import render


def test_menus(request):
    return render(request, 'test_menus.html', {})
