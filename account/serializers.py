from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Institution

class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = "__all__"   
        extra_kwargs = {
            'password': {'write_only': True}
        }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Overriding the username field configuration since your identifier is 'code'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()

    def validate(self, attrs):
        # Authenticates against your USERNAME_FIELD ("code")
        data = super().validate(attrs)
        user = self.user
        
        # Inject matching institution user details into the JSON payload safely
        data['status'] = True
        data['message'] = "Login successful"
        data['user'] = {
            'id': user.id,
            'name': user.name,
            'code': user.code,
            'email': user.email,
            'mobile': user.mobile,
            'gstin': user.gstin,
            'logo': user.logo.url if user.logo else None,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'active': user.active
        }
        
        return data