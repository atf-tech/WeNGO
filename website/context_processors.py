from dashboard.models import Services


def global_services(request):
    """Make the services queryset available globally to all templates."""
    services = Services.objects.all().order_by("display_order")
    return {
        "services": services,
    }

