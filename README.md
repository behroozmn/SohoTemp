# Installation

`install Debian 12` with all configuration

```shell
su root
echo 'export HISTTIMEFORMAT="%Y/%m/%d %T "' >>  /etc/profile.d/soho.sh; #[Add]: export HISTTIMEFORMAT="%Y/%m/%d %T "
chmod 644 /etc/profile.d/soho.sh
/usr/bin/sed  -i s/deb\ cdrom/#deb\ cdrom/g /etc/apt/sources.list   # comment CDROM repository
apt clean all
apt update
sudo -i
sudo apt install bash-completion vim sudo lshw wget curl build-essential nmap mlocate net-tools python3-venv
sudo /sbin/usermod -aG sudo user
sudo shutdown -r now
```

# DRF

File: `setting.py`

```python
INSTALL_APPS = [..., 'rest_framework', ...]
```

File: `urls.py`

```python
from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('rest_framework.urls'))
]
```

```shell
# (.venv)
pip install djangorestframework
pip install markdown
pip install django-filter 
pip install psutil
pip install django-cors-headers

python3 manage.py makemigrations
python3 manage.py migrate
```

```shell
python3 manage.py createsuperuser
```

## Swagger

```shell
pip install drf-spectacular
```

File: `Setting.py`

ALLOWED_HOSTS = ['*'] # behroozMohamadinasab

* `INSTALL_APPS=[... , 'drf_spectacular' ,...]` # Swagget

  ```python
  REST_FRAMEWORK = {
      'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
      #     'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.BasicAuthentication'],
      #     'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated']
  }
  
  SPECTACULAR_SETTINGS = {
      'TITLE': 'Your Project API',
      'DESCRIPTION': 'Your project description',
      'VERSION': '1.0.0',
      'SERVE_INCLUDE_SCHEMA': False,
  }
  ```

File: `urls.py`

```python
from django.contrib import admin
from . import views
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('rest_framework.urls')),

    # YOUR PATTERNS
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Optional UI:
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('memory', views.memory),
    path('cpu', views.cpu),
    path('network', views.network),
    path('disk', views.disk),
]
```

# ZFS(.deb)

```bash
sudo apt update
sudo apt install python3-packaging python3-distlib python3-wheel  python3-pip python3-venv python3-cython-blis
echo $?
sudo apt install build-essential make gcc autoconf libtool dracut alien python3-setuptools python3-cffi python3-distutils  libpython3-stdlib libelf-dev python3 python3-dev fakeroot linux-headers-$(uname -r) zlib1g-dev uuid-dev libblkid-dev libselinux-dev libssl-dev parted lsscsi wget git git autoconf automake libtool alien fakeroot dkms 
echo $?
sudo apt install libffi-dev libselinux1-dev  libncurses5-dev libsystemd-dev pkg-config  debconf debconf-utils file  libc6-dev  lsb-release perl  linux-libc-dev libudev1  libuuid1 init-system-helpers libblkid1 libatomic1  libssl3 zlib1g libcurl4 libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev libaio-dev libattr1-dev 
echo $?
```

> https://packages.debian.org/bookworm/`NAME` [URL](https://packages.debian.org/bookworm/libzfsbootenv1linux)
> https://packages.debian.org/bookworm/amd64/`NAME`/download [URL](https://packages.debian.org/bookworm/amd64/libzfsbootenv1linux/download)

```shell
wget http://ftp.us.debian.org/debian/pool/main/g/glibc/libc6_2.36-9+deb12u10_amd64.deb                            #libc6_2.36-9+deb12u10_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/libnvpair3linux_2.1.11-1+deb12u1_amd64.deb          #libnvpair3linux_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/main/libt/libtirpc/libtirpc3_1.3.3+ds-1_amd64.deb                       #libtirpc3_1.3.3+ds-1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/main/libt/libtirpc/libtirpc-common_1.3.3+ds-1_all.deb                  #ibtirpc-common_1.3.3+ds-1_all.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/libuutil3linux_2.1.11-1+deb12u1_amd64.deb           #libuutil3linux_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/libzfs4linux_2.1.11-1+deb12u1_amd64.deb             #libzfs4linux_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/libzfsbootenv1linux_2.1.11-1+deb12u1_amd64.deb      #libzfsbootenv1linux_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/libzfslinux-dev_2.1.11-1+deb12u1_amd64.deb          #libzfslinux-dev_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/libzpool5linux_2.1.11-1+deb12u1_amd64.deb           #libzpool5linux_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/p/py-libzfs/python3-libzfs_0.0+git20230207.c1bd4a0-1_amd64.deb  #python3-libzfs_0.0+git20230207.c1bd4a0-1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/zfs-dkms_2.1.11-1+deb12u1_all.deb                   #zfs-dkms_2.1.11-1+deb12u1_all.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/zfs-dracut_2.1.11-1+deb12u1_all.deb                 #zfs-dracut_2.1.11-1+deb12u1_all.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/zfsutils-linux_2.1.11-1+deb12u1_amd64.deb           #zfsutils-linux_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/zfs-zed_2.1.11-1+deb12u1_amd64.deb                  #zfs-zed_2.1.11-1+deb12u1_amd64.deb
#http://ftp.us.debian.org/debian/pool/main/g/glibc/libc6-udeb_2.36-9+deb12u10_amd64.udeb

sudo dpkg -i *.deb
echo $?

zfs version # باید نشان دهد
```

## Test

```shell
python3 -c "import libzfs; print('Module installed successfully') ;print(libzfs.__doc__)"
```

[URL](https://installati.one/debian/12/)

# HTTP

Success:

```
{
    "ok": true,
    "error": null,
    "message": "",
    "data": ["john", "mary", "root"],
    "details": {
        "count": 3,
        "include_system": true
    },
    "meta": {
        "timestamp": "2025-09-24T12:34:56Z",
        "response_status_code": ""
    },
    "request_data": {}
}
```

Error:

```
{
    "ok": false,
    "error": {
        "code": "modules_error",
        "message": "Unexpected error while reading user list",
        "extra": {
            "exception": "PermissionError"
            "exception_etails": 
        }
    },
    "data": null,
    "details": {},
    "meta": {
        "timestamp": "2025-09-24T12:45:00Z",
        "response_status_code": ""
    }
}
```


# NGINX
```shell
server {
    listen 80;
    server_name _;

    # 1.(React)
    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_cache_bypass $http_upgrade;
    }

    # 2.(DRF API)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media/ {
        proxy_pass http://127.0.0.1:8000;
    }
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
    }
}

```


## CORS
File:setting.py
```shell
pip install django-cors-headers
```

```python

INSTALLED_APPS = [
    ...
    'corsheaders',
    ...
]
# اضافه کردن middleware در بالاتر از CommonMiddleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://192.168.100.108:5173",
    "http://192.168.100.108",
    "http://10.0.20.245:5173",
    "http://127.0.0.1:5173",
]
```


## soho_core_api

```shell
sudo mkdir -p /var/log/soho_core_api
sudo chown user:user /var/log/soho_core_api
sudo chmod 755 /var/log/soho_core_api
```
sudo vim /etc/systemd/system/soho_core_api.service

```
[Unit]
Description=Gunicorn daemon for soho_core_api
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/soho_core_api
Environment="PATH=/opt/soho_core_api/.venv/bin"

# ذخیره لاگ‌ها در فایل‌های جداگانه
ExecStart=/opt/soho_core_api/.venv/bin/gunicorn \
          --bind 0.0.0.0:8000 \
          --workers 10 \
          --access-logfile /var/log/soho_core_api/access.log \
          --error-logfile /var/log/soho_core_api/error.log \
          --log-level info \
          soho_core_api.wsgi:application

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target  # نشان می‌دهد که این سرویس باید هنگام بوت سیستم (در حالت عادی چندکاربره) به‌صورت خودکار اجرا شود. 
```


