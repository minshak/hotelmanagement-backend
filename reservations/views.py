from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction
from rest_framework.decorators import action
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Image

from datetime import datetime

from .models import CheckIn, CheckOut
from .serializer import CheckInSerializer, CheckOutSerializer
from master.models import Room
from account.models import Institution
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
            raise ValidationError({"room": "Room is already occupied."})

        if CheckIn.objects.filter(room=room, status="CHECKED_IN").exists():
            raise ValidationError({"room": "This room already has an active check-in."})

        serializer.save(status="CHECKED_IN")
        room.status = "OCCUPIED"
        room.save(update_fields=["status"])

    @action(detail=True, methods=['get'], url_path='download-receipt')
    def download_receipt(self, request, pk=None):
        """
        GET /api/reservations/checkins/{id}/download-receipt/
        Generates and drops an authenticated binary PDF check-in acknowledgement receipt.
        """
        try:
            checkin = CheckIn.objects.get(pk=pk)
        except CheckIn.DoesNotExist:
            return Response({"error": "Check-in instance context missing."}, status=status.HTTP_404_NOT_FOUND)
            
        customer = checkin.customer
        room = checkin.room
        base_rent = float(getattr(checkin, 'base_daily_rent', 0.0) or getattr(room.room_type, 'rent', 0.0))

        # Setup Response 
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="CheckIn_Receipt_ARR-{checkin.id:06d}.pdf"'

        # Build PDF Design Geometry
        doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'DocTitle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor("#1A365D"), spaceAfter=15
        )
        section_style = ParagraphStyle(
            'SecTitle', parent=styles['Heading2'], fontSize=12, leading=16, textColor=colors.HexColor("#2B6CB0"), spaceBefore=12, spaceAfter=6
        )
        normal_style = styles['Normal']

        # Title Layout Block
        institution = Institution.objects.filter(active=True).first()

        story.append(Paragraph(institution.name,title_style))
        if institution.logo:
            logo = Image(institution.logo.path, width=80, height=80)
            story.append(logo)
        story.append(Paragraph(institution.address,normal_style))
        story.append(Paragraph("CHECK-IN / ADVANCE  RECEIPT", normal_style))
        story.append(Paragraph(f"<b>Receipt Reference:</b> ARR-{checkin.id:06d}", normal_style))
        story.append(Paragraph(institution.gstin, normal_style))
        story.append(Paragraph(f"<b>Date:</b> {checkin.checkin_date} @ {checkin.checkin_time}", normal_style))
        story.append(Spacer(1, 15))

        # Core Metadata Rows
        story.append(Paragraph("Registration & Guest Profiles", section_style))
        info_data = [
            [Paragraph("<b>Guest Name:</b>", normal_style), Paragraph(str(customer.customer_name), normal_style)],
            [Paragraph("<b>Mobile No:</b>", normal_style), Paragraph(str(getattr(customer, 'mobile_no', 'N/A')), normal_style)],
            [Paragraph("<b>Assigned Unit:</b>", normal_style), Paragraph(f"Room {room.room_no} ({room.room_type.category})", normal_style)],
        ]
        info_table = Table(info_data, colWidths=[120, 400])
        info_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
        story.append(info_table)
        story.append(Spacer(1, 15))

        # Financial Calculations Matrix Table
        story.append(Paragraph("Financial Summary Breakdown", section_style))
        ledger_data = [
            ["Description", "Payment Mode / Reference", "Amount"],
            ["Base Daily Rent Rate", "Standard Category Charging Rule", f"₹{base_rent:.2f}"],
            ["Advance Amount Paid", f"Settled via {checkin.pay_mode}", f"₹{float(checkin.advance_amount):.2f}"],
            ["Outstanding Balance Due", "Payable upon checkout execution", f"₹{float(checkin.pending_amount):.2f}"],
            ["Total Structural Commitment", "", f"₹{float(checkin.total_amount):.2f}"]
        ]
        
        ledger_table = Table(ledger_data, colWidths=[180, 200, 140])
        ledger_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2D3748")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor("#CBD5E0")),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor("#1A365D")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
           
        story.append(ledger_table)
        story.append(Spacer(1, 15))

        # Remarks Block
        remarks_val = checkin.remarks or "No structural customer remarks stated."
        story.append(Paragraph(f"<b>Internal Remarks / Notes:</b> {remarks_val}", normal_style))

        doc.build(story)
        return response
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
    
    queryset = CheckOut.objects.select_related(
        'checkin__customer', 
        'checkin__room',
        'checkin__room__room_type'
    ).all().order_by("-id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        checkin = serializer.validated_data["checkin"]

        checkin_datetime = datetime.combine(checkin.checkin_date, checkin.checkin_time)
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

        with transaction.atomic():
            checkout = serializer.save(
                total_days=total_days,
                balance_paid=balance
            )

            checkin.total_amount = total_amount
            checkin.pending_amount = 0  
            checkin.status = "CHECKED_OUT"
            checkin.save(update_fields=['total_amount', 'pending_amount', 'status'])

            room = checkin.room
            room.status = "AVAILABLE"
            room.save(update_fields=['status'])

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

        # --- FIX: Define the rent variable in this local scope ---
        rent = getattr(room.room_type, 'rent', 0.0)

        # Gracefully handle room type dynamically 
        room_type_name = getattr(room.room_type, 'name', str(room.room_type))

        # Safeguard fallback values if fields don't exist on checkin model
        base_rent = float(getattr(checkin, 'base_daily_rent', None) or rent)

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
                "base_daily_rent": base_rent,
                "subtotal": float(base_rent * checkout.total_days),
                "advance_paid": float(checkin.advance_amount),
                "balance_paid": float(checkout.balance_paid),
                "total_amount_charged": float(checkin.total_amount),
                "payment_mode": checkout.pay_mode,
            },
            "remarks": checkout.remarks or "Thank you for staying with us!"
        }

        return Response(receipt_data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'], url_path='download-receipt')
    def download_receipt(self, request, pk=None):
        """
        GET /api/checkouts/{id}/download-receipt/
        Generates and downloads a professional PDF receipt.
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
        rent = getattr(room.room_type, 'rent', 0.0)
        base_rent = float(getattr(checkin, 'base_daily_rent', None) or rent)

        # 1. Create the HTTP Response with PDF headers
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Receipt_REC-{checkout.id:06d}.pdf"'

        # 2. Build the PDF Document using ReportLab
        doc = SimpleDocTemplate(
            response, 
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        story = []

        # Custom styles for a clean layout
        title_style = ParagraphStyle(
            'TitleStyle', 
            parent=styles['Heading1'], 
            fontSize=24, 
            leading=28, 
            textColor=colors.HexColor("#1A365D"), 
            spaceAfter=12
        )
        section_style = ParagraphStyle(
            'SectionStyle', 
            parent=styles['Heading2'], 
            fontSize=14, 
            leading=18, 
            textColor=colors.HexColor("#2B6CB0"), 
            spaceBefore=10, 
            spaceAfter=6
        )
        normal_style = styles['Normal']
        institution = Institution.objects.filter(active=True).first()


        # Header Title
        story.append(Paragraph(institution.name,title_style))
        if institution.logo:
            logo = Image(institution.logo.path, width=80, height=80)
            story.append(logo)
        story.append(Paragraph(institution.address,normal_style))
        story.append(Paragraph(" RECEIPT", normal_style))
        story.append(Paragraph(f"<b>Receipt No:</b> REC-{checkout.id:06d}", normal_style))
        story.append(Paragraph(institution.gstin, normal_style))
        story.append(Paragraph(f"<b>Date:</b> {checkout.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(checkout.created_at, 'strftime') else checkout.created_at}", normal_style))
        story.append(Spacer(1, 15))

        # Customer & Stay Details Table
        story.append(Paragraph("Stay Details", section_style))
        details_data = [
            [Paragraph("<b>Customer Name:</b>", normal_style), Paragraph(customer.customer_name, normal_style)],
            [Paragraph("<b>Room No:</b>", normal_style), Paragraph(str(room.room_no), normal_style)],
            [Paragraph("<b>Room Type:</b>", normal_style), Paragraph(getattr(room.room_type, 'name', str(room.room_type)), normal_style)],
            [Paragraph("<b>Check-in:</b>", normal_style), Paragraph(f"{checkin.checkin_date} {checkin.checkin_time}", normal_style)],
            [Paragraph("<b>Check-out:</b>", normal_style), Paragraph(f"{checkout.checkout_date} {checkout.checkout_time}", normal_style)],
            [Paragraph("<b>Total Duration:</b>", normal_style), Paragraph(f"{checkout.total_days} Day(s)", normal_style)],
        ]
        
        details_table = Table(details_data, colWidths=[120, 400])
        details_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 15))

        # Financial Breakdown Table
        story.append(Paragraph("Financial Breakdown", section_style))
        subtotal = base_rent * checkout.total_days
        
        financial_data = [
            ["Description", "Calculation", "Amount"],
            [f"Room Rent ({getattr(room.room_type, 'name', 'Room')})", f"${base_rent:.2f} x {checkout.total_days} days", f"${subtotal:.2f}"],
            ["Advance Paid", "", f"-${float(checkin.advance_amount):.2f}"],
            ["Balance Settled", f"via {checkout.pay_mode}", f"${float(checkout.balance_paid):.2f}"],
            ["Total Amount Charged", "", f"${float(checkin.total_amount):.2f}"]
        ]

        fin_table = Table(financial_data, colWidths=[200, 180, 140])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2D3748")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor("#CBD5E0")),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor("#1A365D")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), # Bold the Total line
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(fin_table)
        story.append(Spacer(1, 20))

        # Remarks
        remarks_text = checkout.remarks or "Thank you for staying with us!"
        story.append(Paragraph(f"<b>Remarks:</b> {remarks_text}", normal_style))

        # Generate Document
        doc.build(story)
        return response