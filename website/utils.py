import random
from django.apps import apps

def generate_receipt_number():
    models_to_check = [
        "HomeDonation",
        "ServiceDonation",       
    ]

    while True:
        number = f"WNG-{random.randint(0, 999999):06d}"
        exists = False

        for model_name in models_to_check:
            model = apps.get_model("website", model_name)

            if model.objects.filter(receipt_no=number).exists():
                exists = True
                break

        if not exists:
            return number