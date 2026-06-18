from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        return {
            "status": True,
            "message": "Login successful",
            "access": data["access"],
            "refresh": data["refresh"],
        }