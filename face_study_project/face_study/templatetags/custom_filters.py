from django import template

register = template.Library()

@register.filter
def get_range(value):
    """
    Returns a range from 1 to value inclusive.
    Usage in template: {{ emotions.count|get_range }}
    """
    return range(1, int(value) + 1)

@register.filter
def mul(value, arg):
    """Multiplica o valor pelo argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        try:
            return value * arg
        except Exception:
            return ""

@register.filter
def add(value, arg):
    """Adiciona o argumento ao valor"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except Exception:
            return ""

@register.filter
def subtract(value, arg):
    """Subtrai o argumento do valor"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except Exception:
            return ""

@register.filter
def divide(value, arg):
    """Divide o valor pelo argumento"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return ""