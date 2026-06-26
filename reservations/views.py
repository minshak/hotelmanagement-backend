from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
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

class CheckOutViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CheckOut.objects.all().order_by("-id")
    serializer_class = CheckOutSerializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        checkin = serializer.validated_data["checkin"]

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

        rent = checkin.room.room_type.rent
        total_amount = rent * total_days
        balance = total_amount - checkin.advance_amount

        checkout = serializer.save(
            total_days=total_days,
            balance_paid=balance
        )

        checkin.status = "CHECKED_OUT"
        checkin.save()

        room = checkin.room
        room.status = "AVAILABLE"
        room.save()

        return Response(
            CheckOutSerializer(checkout).data,
            status=status.HTTP_201_CREATED
        )