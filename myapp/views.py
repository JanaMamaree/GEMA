from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import Prediction, Location, DeviceIP
from .serializers import PredictionSerializer, LocationSerializer, DeviceIPSerializer
from django.contrib.auth.decorators import login_required

class PredictionCreateView(generics.CreateAPIView):
    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer

class LocationCreateView(generics.CreateAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        broadcast_device_status_update()

class DeviceIPUpsertView(APIView):
    def post(self, request, *args, **kwargs):
        device_id = request.data.get('device_id')
        ip_address = request.data.get('ip_address')

        if not device_id or not ip_address:
            return Response(
                {'error': 'device_id and ip_address are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj, created = DeviceIP.objects.update_or_create(
            device_id=device_id,
            defaults={
                'ip_address': ip_address,
                'timestamp': timezone.now(),
            }
        )

        serializer = DeviceIPSerializer(obj)
        response = Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

        broadcast_device_status_update()

        return response


class DeviceStatusView(APIView):
    def get(self, request, *args, **kwargs):
        devices = DeviceIP.objects.values('device_id').distinct()
        data = []
        now = timezone.now()

        for device in devices:
            device_id = device['device_id']
            last_ip = DeviceIP.objects.filter(device_id=device_id).order_by('-timestamp').first()
            last_location = Location.objects.filter(device_id=device_id).order_by('-timestamp').first()

            if last_ip and (now - last_ip.timestamp <= timedelta(minutes=1)):
                status = "ONLINE"
            else:
                status = "OFFLINE"

            if last_location and (now - last_location.timestamp <= timedelta(minutes=1)):
                mode = "MOVING"
                last_active = "NOW"
            else:
                mode = "IDLE"
                if last_location:
                    last_active_time = last_location.timestamp + timedelta(hours=2)
                    last_active = last_active_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    last_active = "N/A"

            ip_address = last_ip.ip_address if last_ip else ""

            data.append({
                "device_id": device_id,
                "ip": ip_address,
                "status": status,
                "mode": mode,
                "last_active": last_active,
            })

        return Response(data)


from django.shortcuts import render

@login_required
def device_page(request):
    return render(request, 'myapp/device.html')

from django.http import JsonResponse

def get_last_location(request, device_id):
    try:
        last_entry = Location.objects.filter(device_id=device_id).latest('timestamp')
        return JsonResponse({
            'success': True,
            'lat': last_entry.latitude,
            'lon': last_entry.longitude
        })
    except Location.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No location found'}, status=404)

from rest_framework.decorators import api_view

@api_view(['GET'])
def device_predictions(request, device_id):
    predictions = Prediction.objects.filter(device_id=device_id).order_by('-timestamp')
    serializer = PredictionSerializer(predictions, many=True)
    return Response(serializer.data)

@login_required
def map_page(request):
    return render(request, 'myapp/map.html')

@api_view(['GET'])
def device_locations(request, device_id):
    locations = Location.objects.filter(device_id=device_id).order_by('timestamp')
    serializer = LocationSerializer(locations, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def all_predictions(request):
    queryset = Prediction.objects.all()
    serializer = PredictionSerializer(queryset, many=True)
    return Response(serializer.data)

@login_required
def history_page(request):
    return render(request, 'myapp/history.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_protect

@login_required
def deactivate_account(request):
    if request.method == "POST":
        user = request.user
        user.is_active = False
        user.save()
        logout(request)
        return redirect('login')
    return redirect('profile')

@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        return redirect('register')
    return redirect('profile')

@csrf_protect
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect('login')
    return redirect('profile')

@login_required
def profile(request):
    user = request.user
    success = ""
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        if username and username != user.username:
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                error = "Username already exists."
            else:
                user.username = username

        if email and email != user.email:
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                error = "Email already exists."
            else:
                user.email = email

        if phone and hasattr(user, 'userprofile'):
            user.userprofile.phone = phone
            user.userprofile.save()

        if password:
            user.set_password(password)

        if not error:
            user.save()
            success = "Profile updated successfully."
    return render(request, "myapp/profile.html", {"user": user, "success": success, "error": error})

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import UserProfile
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

def register(request):
    error = ""
    success = ""
    initial = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        phone = request.POST.get("phone", "").strip()

        if not username or not email or not password or not phone:
            error = "All fields are required."
            initial = {"username": username, "email": email, "phone": phone}
        elif User.objects.filter(username=username).exists():
            error = "Username already exists."
            initial = {"username": username, "email": email, "phone": phone}
        elif User.objects.filter(email=email).exists():
            error = "Email already exists."
            initial = {"username": username, "email": email, "phone": phone}
        else:
            try:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.is_active = False
                user.save()
                UserProfile.objects.create(user=user, phone=phone)
                current_site = get_current_site(request)
                activation_link = f"http://{current_site.domain}{reverse('activate', args=[urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)])}"
                subject = 'Activate your account'
                message = f"Please click the link below to activate your account:\n{activation_link}"
                send_mail(subject, message, None, [user.email])
                success = "Registration successful! Please check your email to activate your account."
                initial = {}
            except IntegrityError:
                error = "A user with that username or email already exists."
                initial = {"username": username, "email": email, "phone": phone}
    return render(request, "myapp/register.html", {"error": error, "success": success, "initial": initial})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('/login/?activated=1')
    else:
        return redirect('register')

from django.contrib.auth import authenticate, login

def login_view(request):
    error = ""
    activated = request.GET.get("activated")
    activated_message = ""
    if activated:
        activated_message = "Your account is activated. You can now log in."
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("map_page")
            else:
                error = "Your account is not active. Please check your email to activate your account."
        else:
            try:
                user_obj = User.objects.get(username=username)
                if not user_obj.is_active:
                    error = "Your account is not active. Please check your email to activate your account."
                else:
                    error = "Invalid username or password."
            except User.DoesNotExist:
                error = "Invalid username or password."
    return render(request, "myapp/login.html", {"error": error, "activated_message": activated_message})



# --- Broadcast function moved here ---

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_device_status_update():
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[Broadcast] broadcast_device_status_update called")  # DEBUG
    devices = DeviceIP.objects.values('device_id').distinct()
    data = []
    now = timezone.now()
    for device in devices:
        device_id = device['device_id']
        last_ip = DeviceIP.objects.filter(device_id=device_id).order_by('-timestamp').first()
        last_location = Location.objects.filter(device_id=device_id).order_by('-timestamp').first()
        if last_ip and (now - last_ip.timestamp <= timedelta(minutes=1)):
            status = "ONLINE"
        else:
            status = "OFFLINE"
        if last_location and (now - last_location.timestamp <= timedelta(minutes=1)):
            mode = "MOVING"
            last_active = "NOW"
        else:
            mode = "IDLE"
            if last_location:
                last_active_time = last_location.timestamp + timedelta(hours=2)
                last_active = last_active_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_active = "N/A"
        ip_address = last_ip.ip_address if last_ip else ""
        data.append({
            "device_id": device_id,
            "ip": ip_address,
            "status": status,
            "mode": mode,
            "last_active": last_active,
        })
    logger.info(f"[Broadcast] Sending device.status to channel layer: {data}")  # DEBUG
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "device_status",
        {
            "type": "device.status",
            "data": data
        }
    )
