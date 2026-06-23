from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import CheckIn
from .serializer import CheckInSerializer
from .models import CheckOut
from .serializer import CheckOutSerializer
from rest_framework.permissions import IsAuthenticated



class CheckInViewSet(viewsets.ModelViewSet): 
    permission_classes  = [IsAuthenticated]
    queryset = CheckIn.objects.all()
    serializer_class = CheckInSerializer


class CheckOutViewSet(viewsets.ModelViewSet):
    permission_classes  = [IsAuthenticated]
    queryset = CheckOut.objects.all()
    serializer_class = CheckOutSerializer