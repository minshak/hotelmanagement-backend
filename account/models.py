import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

class InstitutionManager(BaseUserManager):

    def create_user(self, code, password=None, **extra_fields):
        if not code:
            raise ValueError("Institution code is required")

        user = self.model(code=code, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, code, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("active", True)

        return self.create_user(code, password, **extra_fields)
    
class Institution(AbstractBaseUser, PermissionsMixin):

    name = models.CharField(max_length=200)

    code = models.CharField(
        max_length=20,
        unique=True
    )

    address = models.TextField()

    logo = models.ImageField(
        upload_to="institution/logo/",
        blank=True,
        null=True
    )

    mobile = models.CharField(max_length=15)

    email = models.EmailField()

    gstin = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    active = models.BooleanField(default=True)

    is_staff = models.BooleanField(default=False)

    objects = InstitutionManager()

    USERNAME_FIELD = "code"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "admn_instn_master"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.active