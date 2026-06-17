from rest_framework import serializers
from .models import  CheckIn
from .models import CheckOut



class CheckInSerializer(serializers.ModelSerializer):

    class Meta:
        model = CheckIn
        fields = "__all__"



class CheckOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckOut
        fields = "__all__"