from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import CheckIn
from .serializer import CheckInSerializer
from .models import CheckOut
from .serializer import CheckOutSerializer



class CheckInViewSet(viewsets.ModelViewSet):
    queryset = CheckIn.objects.all()
    serializer_class = CheckInSerializer


class CheckOutViewSet(viewsets.ModelViewSet):
    queryset = CheckOut.objects.all()
    serializer_class = CheckOutSerializer