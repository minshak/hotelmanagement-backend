from django.db import models

# Create your models here.
from django.db import models
from master.models import Room, Customer


class CheckIn(models.Model):

    PAYMENT_MODES = [
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("UPI", "UPI"),
        ("NET_BANKING", "Net Banking"),
    ]

    STATUS_CHOICES = [
        ("CHECKED_IN", "Checked In"),
        ("CHECKED_OUT", "Checked Out"),
        ("CANCELLED", "Cancelled"),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="checkins"
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="checkins"
    )

    checkin_date = models.DateField()

    checkin_time = models.TimeField()

    advance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    pending_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    pay_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="CHECKED_IN"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.customer_name} - Room {self.room.room_no}"
    

class CheckOut(models.Model):

    PAYMENT_TYPES = [
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("UPI", "UPI"),
        ("NET_BANKING", "Net Banking"),
    ]

    checkin = models.OneToOneField(
        CheckIn,
        on_delete=models.PROTECT,
        related_name="checkout"
    )

    checkout_date = models.DateField()

    checkout_time = models.TimeField()

    total_days = models.PositiveIntegerField()

    balance_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    pay_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Checkout - {self.checkin.customer.customer_name}"