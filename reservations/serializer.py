from rest_framework import serializers
from .models import  CheckIn
from .models import CheckOut



class CheckInSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.customer_name",
        read_only=True
    )

    mobile_no = serializers.CharField(
        source="customer.mobile_no",
        read_only=True
    )

    room_no = serializers.CharField(
        source="room.room_no",
        read_only=True
    )

    class Meta:
        model = CheckIn
        fields = "__all__"

class CheckOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckOut
        fields = "__all__"