from django.contrib import admin
from .models import Prediction, Location, DeviceIP

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'latitude', 'longitude', 'timestamp')

@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'label', 'latitude', 'longitude', 'timestamp')

@admin.register(DeviceIP)
class DeviceIPAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'ip_address', 'timestamp')

from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False

class UserAdmin(admin.ModelAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'email', 'get_phone', 'is_staff', 'is_active')

    def get_phone(self, obj):
        return obj.userprofile.phone if hasattr(obj, 'userprofile') else ''
    get_phone.short_description = 'Phone'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)