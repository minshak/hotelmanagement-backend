from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction
from rest_framework.decorators import action

from datetime import datetime

from .models import CheckIn, CheckOut
from .serializer import CheckInSerializer, CheckOutSerializer
from master.models import Room
class CheckInViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckInSerializer
    queryset = CheckIn.objects.all().order_by("-id")

    def get_queryset(self):
        status_param = self.request.query_params.get("status")

        if status_param:
            return CheckIn.objects.filter(status=status_param).order_by("-id")

        return CheckIn.objects.filter(status="CHECKED_IN").order_by("-id")

    def perform_create(self, serializer):
        room = serializer.validated_data["room"]

        if room.status != "AVAILABLE":
            raise ValidationError(
                {"room": "Room is already occupied."}
            )

        if CheckIn.objects.filter(
            room=room,
            status="CHECKED_IN"
        ).exists():
            raise ValidationError(
                {"room": "This room already has an active check-in."}
            )

        serializer.save(status="CHECKED_IN")

        room.status = "OCCUPIED"
        room.save(update_fields=["status"])
from math import ceil
from datetime import datetime
from datetime import datetime
from math import ceil

# class CheckOutViewSet(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     queryset = CheckOut.objects.all().order_by("-id")
#     serializer_class = CheckOutSerializer

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         checkin = serializer.validated_data["checkin"]

#         # Calculate durations
#         checkin_datetime = datetime.combine(
#             checkin.checkin_date,
#             checkin.checkin_time
#         )
#         checkout_datetime = datetime.combine(
#             serializer.validated_data["checkout_date"],
#             serializer.validated_data["checkout_time"]
#         )

#         duration = checkout_datetime - checkin_datetime
#         hours = duration.total_seconds() / 3600
#         total_days = max(1, ceil(hours / 24))

#         # Calculate final financial breakdown
#         rent = checkin.room.room_type.rent
#         total_amount = rent * total_days
#         balance = total_amount - checkin.advance_amount

#         # Use an atomic block to ensure all database updates succeed together
#         with transaction.atomic():
#             # 1. Save Checkout record
#             checkout = serializer.save(
#                 total_days=total_days,
#                 balance_paid=balance
#             )

#             # 2. Update parent CheckIn entry with the calculated total and clear pending
#             checkin.total_amount = total_amount
#             checkin.pending_amount = 0  # Assuming balance is fully paid at checkout
#             checkin.status = "CHECKED_OUT"
#             checkin.save(update_fields=['total_amount', 'pending_amount', 'status'])

#             # 3. Direct update to make certain the room gets freed
#             room = checkin.room
#             room.status = "AVAILABLE"
#             room.save(update_fields=['status'])

#         return Response(
#             CheckOutSerializer(checkout).data,
#             status=status.HTTP_201_CREATED
#         )


class CheckOutViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckOutSerializer
    
    # Using select_related minimizes DB hits for nested relations during listings and receipt creation
    queryset = CheckOut.objects.select_related(
        'checkin__customer', 
        'checkin__room',
        'checkin__room__room_type'
    ).all().order_by("-id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        checkin = serializer.validated_data["checkin"]

        # Calculate durations
        checkin_datetime = datetime.combine(
            checkin.checkin_date,
            checkin.checkin_time
        )
        checkout_datetime = datetime.combine(
            serializer.validated_data["checkout_date"],
            serializer.validated_data["checkout_time"]
        )

        duration = checkout_datetime - checkin_datetime
        hours = duration.total_seconds() / 3600
        total_days = max(1, ceil(hours / 24))

        # Calculate final financial breakdown
        rent = checkin.room.room_type.rent
        total_amount = rent * total_days
        balance = total_amount - checkin.advance_amount

        # Use an atomic block to ensure all database updates succeed together
        with transaction.atomic():
            # 1. Save Checkout record
            checkout = serializer.save(
                total_days=total_days,
                balance_paid=balance
            )

            # 2. Update parent CheckIn entry with the calculated total and clear pending
            checkin.total_amount = total_amount
            checkin.pending_amount = 0  # Assuming balance is fully paid at checkout
            checkin.status = "CHECKED_OUT"
            checkin.save(update_fields=['total_amount', 'pending_amount', 'status'])

            # 3. Direct update to make certain the room gets freed
            room = checkin.room
            room.status = "AVAILABLE"
            room.save(update_fields=['status'])

        # Using explicit context serialization to match custom readout formatting
        return Response(
            self.get_serializer(checkout).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], url_path='receipt')
    def receipt(self, request, pk=None):
        """
        GET /api/checkouts/{id}/receipt/
        Generates a detailed receipt payload for a given checkout instance.
        """
        try:
            checkout = self.get_queryset().get(pk=pk)
        except CheckOut.DoesNotExist:
            return Response(
                {"error": "Checkout record not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        checkin = checkout.checkin
        customer = checkin.customer
        room = checkin.room

        # Gracefully handle room type dynamically 
        room_type_name = getattr(room.room_type, 'name', str(room.room_type))

        receipt_data = {
            "receipt_no": f"REC-{checkout.id:06d}",
            "generated_at": checkout.created_at,
            "customer": {
                "name": customer.customer_name,
            },
            "stay_details": {
                "room_no": room.room_no,
                "room_type": room_type_name,
                "checkin_datetime": f"{checkin.checkin_date} {checkin.checkin_time}",
                "checkout_datetime": f"{checkout.checkout_date} {checkout.checkout_time}",
                "total_days": checkout.total_days,
            },
            "financial_breakdown": {
                "base_daily_rent": float(checkin.base_daily_rent or rent),
                "subtotal": float((checkin.base_daily_rent or rent) * checkout.total_days),
                "advance_paid": float(checkin.advance_amount),
                "balance_paid": float(checkout.balance_paid),
                "total_amount_charged": float(checkin.total_amount),
                "payment_mode": checkout.pay_mode,
            },
            "remarks": checkout.remarks or "Thank you for staying with us!"
        }

        return Response(receipt_data, status=status.HTTP_200_OK)