from django.utils.timezone import now


def year(request):
    """ Добавляется переменная с текущим годом"""
    return {
        'year': now().year
    }
