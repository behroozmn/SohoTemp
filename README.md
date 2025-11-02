# Installation

## OS

`install Debian 12` with all configuration

```shell
su root
echo 'export HISTTIMEFORMAT="%Y/%m/%d %T "' >>  /etc/profile.d/soho.sh; #[Add]: export HISTTIMEFORMAT="%Y/%m/%d %T "
chmod 644 /etc/profile.d/soho.sh
/usr/bin/sed  -i s/deb\ cdrom/#deb\ cdrom/g /etc/apt/sources.list   # comment CDROM repository
apt clean all
apt update
apt install sudo
/sbin/usermod -aG sudo user

su user
sudo -i

# Note: نصب ابزارهای عمومی سیستم عامل
sudo apt install bash-completion vim lshw wget curl build-essential  mlocate net-tools wget 

# Note: نصب بسته‌های تخصصی سیستم عامل
sudo apt install cmake nmap

#note: نصب بسته های کرنلی برای سیستم عامل
sudo apt install linux-headers-$(uname -r)

sudo apt install  python3-venv python3-packaging python3-distlib python3-wheel  \
                python3-pip python3-venv python3-cython-blis build-essential make gcc autoconf libtool alien python3-setuptools python3-cffi python3-distutils  \
                libpython3-stdlib libelf-dev python3 python3-dev fakeroot  zlib1g-dev uuid-dev libblkid-dev libselinux-dev libssl-dev parted lsscsi  \
                git git autoconf automake libtool alien fakeroot dkms libffi-dev libselinux1-dev  libncurses5-dev libsystemd-dev pkg-config  debconf debconf-utils file  libc6-dev  \
                lsb-release perl  linux-libc-dev libudev1  libuuid1 init-system-helpers libblkid1 libatomic1  libssl3 zlib1g libcurl4 libblkid-dev uuid-dev libudev-dev libssl-dev \
                zlib1g-dev libaio-dev libattr1-dev 
sudo shutdown -r now
```

# ZFS(.deb)

Downlaod

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
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/zfsutils-linux_2.1.11-1+deb12u1_amd64.deb           #zfsutils-linux_2.1.11-1+deb12u1_amd64.deb
wget http://ftp.us.debian.org/debian/pool/contrib/z/zfs-linux/zfs-zed_2.1.11-1+deb12u1_amd64.deb                  #zfs-zed_2.1.11-1+deb12u1_amd64.deb
#http://ftp.us.debian.org/debian/pool/main/g/glibc/libc6-udeb_2.36-9+deb12u10_amd64.udeb
```

install

```shell
sudo dpkg -i *.deb
echo $?
```

```shell
zfs version # بررسی ورژن

#بررسی اینکه initramfs شامل ماژول‌های ZFS است
lsinitramfs /boot/initrd.img-$(uname -r) | grep -i zfs #اگر خروجی داشت، یعنی همه چیز درست است.  

# بررسی اینکه لایبرری زد اف اس را میفهمد یا خیر
python3 -c "import libzfs; print('Module installed successfully') ;print(libzfs.__doc__);import sys; print(sys.path)"
#OUTPUT:
## ---> Module installed successfully
## ---> None
## ---> ['', '/usr/lib/python311.zip', '/usr/lib/python3.11', '/usr/lib/python3.11/lib-dynload', '/usr/local/lib/python3.11/dist-packages', '/usr/lib/python3/dist-packages', '/usr/lib/python3.11/dist-packages']
```

نکات:

* dracut: در دبیان، سیستم پیش‌فرض برای ساخت initramfs (فایل اولیه‌ی بوت) از initramfs-tools استفاده می‌کند، نه dracut.
    * بسته‌ی dracut معمولاً روی دبیان نصب نیست.
    * و نصب zfs-dracut روی دبیان ضروری نیست و حتی ممکن است باعث مشکل شود.
    * در دبیان، بسته‌ی dracut را نصب نکنید مگر اینکه واقعاً بدانید چه کار می‌کنید.
    * نصب آن ممکن است سیستم بوت شما را خراب کند، چون جایگزین سیستم پیش‌فرض initramfs می‌شود

[URL](https://installati.one/debian/12/)

# PYTHON

## VirtualEnvironments

```shell
cd <Dir>
python3 -m venv .venv --system-site-packages #همراه آوردن بسته‌های داخلی سیستم عامل


# (.venv)
pip install djangorestframework
pip install markdown
pip install django-filter 
pip install psutil
pip install django-cors-headers


python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py createsuperuser
```

## DRF

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

## Swagger

```shell
pip install drf_spectacular
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

## CORS

File:setting.py

```shell
pip install django-cors-headers
```

```python

INSTALLED_APPS = [

    'corsheaders',
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

# NGINX

```shell
server {
    listen 80;
    server_name _;

    # 1. سرو فایل‌های استاتیک React (از dist)
    location / {
        root /opt/soho_ui_react/dist;
        try_files $uri $uri/ /index.html;
        expires 10m;
        add_header Cache-Control "public, immutable";
    }

    # 2. API → Django (Gunicorn)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 3. فایل‌های مدیا و استاتیک (از Django)
    location /media/ {
        proxy_pass http://127.0.0.1:8000;
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8000;
    }
}

```

## systemd: soho_core_api

```shell
sudo mkdir -p /var/log/soho
sudo chown user:user /var/log/soho
sudo chmod 777 /var/log/soho
```

sudo vim /etc/systemd/system/soho_core_api.service

```
[Unit]
Description=Gunicorn daemon for soho_core_api
After=network.target
Before=nginx.service


[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/soho_core_api
Environment="PATH=/opt/soho_core_api/.venv/bin"

# ذخیره لاگ‌ها در فایل‌های جداگانه
ExecStart=/usr/bin/sudo /opt/soho_core_api/.venv/bin/gunicorn \
          --bind 0.0.0.0:8000 \
          --workers 10 \
          --access-logfile /var/log/soho_core_api/access.log \
          --error-logfile /var/log/soho_core_api/error.log \
          --log-level debug \
          soho_core_api.wsgi:application

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target  # نشان می‌دهد که این سرویس باید هنگام بوت سیستم (در حالت عادی چندکاربره) به‌صورت خودکار اجرا شود. 
```

```shell
sudo systemctl enable soho_core_api.service
sudo systemctl daemon-reload
sudo systemctl start soho_core_api.service

```

# Permission

```shell
sudo cat /etc/sudoers.d/Behrooz 
[sudo] password for user: 
user	ALL=(ALL) NOPASSWD: /usr/bin/nmap
user	ALL=(ALL) NOPASSWD: /usr/bin/apt
user	ALL=(ALL) NOPASSWD: /usr/bin/sudo
user	ALL=(ALL) NOPASSWD: /usr/bin/chmod
user	ALL=(ALL) NOPASSWD: /usr/bin/chown
user	ALL=(ALL) NOPASSWD: /usr/bin/vim
user	ALL=(ALL) NOPASSWD: /usr/bin/systemctl
user	ALL=(ALL) NOPASSWD: /usr/bin/updatedb
user	ALL=(ALL) NOPASSWD: /usr/bin/dpkg
user	ALL=(ALL) NOPASSWD: /usr/sbin/shutdown
user	ALL=(ALL) NOPASSWD: /usr/bin/killall
user	ALL=(ALL) NOPASSWD: /usr/bin/kill
user	ALL=(ALL) NOPASSWD: /usr/bin/lnav
user	ALL=(ALL) NOPASSWD: /usr/bin/ls
user	ALL=(ALL) NOPASSWD: /usr/sbin/ifdown
user	ALL=(ALL) NOPASSWD: /usr/sbin/ifup
user	ALL=(ALL) NOPASSWD: /usr/bin/systemctl
user	ALL=(ALL) NOPASSWD: /usr/bin/zpool
user	ALL=(ALL) NOPASSWD: /usr/bin/zfs
user	ALL=(ALL) NOPASSWD: /usr/sbin/wipefs
user	ALL=(ALL) NOPASSWD: /usr/bin/smbpasswd
user	ALL=(ALL) NOPASSWD: /usr/bin/pdbedit
user	ALL=(ALL) NOPASSWD: /opt/soho_core_api/.venv/bin/gunicorn
```

#appendix

اگر نیاز شد

```shell
rm -rf .venv
python3 -m venv .venv --system-site-packages
source ./.venv/bin/activate
```