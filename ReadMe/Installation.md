> install Debian 12


# post installation

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
## VirtualEnvironments

```shell
cd <Dir>
python3 -m venv .venv --system-site-packages
```
cat > /tmp/reqs.txt <<EOF
anyio==3.6.2
asgiref==3.9.1
attrs==25.3.0
blinker==1.5
blis==0.9.1
certifi==2022.9.24
cffi==1.15.1
chardet==5.1.0
charset-normalizer==3.0.1
click==8.1.3
colorama==0.4.6
cryptography==38.0.4
dbus-python==1.3.2
distlib==0.3.6
distro==1.8.0
Django==5.2.5
django-cors-headers==4.7.0
django-filter==25.1
djangorestframework==3.16.1
dnspython==2.3.0
drf-spectacular==0.28.0
gpg==1.18.0
h11==0.14.0
h2==4.1.0
hpack==4.0.0
httpcore==0.16.3
httplib2==0.20.4
httpx==0.23.3
hyperframe==6.0.0
idna==3.3
inflection==0.5.1
jsonschema==4.25.0
jsonschema-specifications==2025.4.1
lazr.restfulclient==0.14.5
lazr.uri==1.0.6
libzfs==1.1
Markdown==3.8.2
markdown-it-py==2.1.0
mdurl==0.1.2
numpy==1.24.2
oauthlib==3.2.2
packaging==23.0
ply==3.11
psutil==7.0.0
pycparser==2.21
pycurl==7.45.2
Pygments==2.14.0
PyGObject==3.42.2
PyJWT==2.6.0
pyparsing==3.0.9
PySimpleSOAP==1.16.2
python-apt==2.6.0
python-debian==0.1.49
python-debianbts==4.0.1
PyYAML==6.0.2
pyzfs==0.2.3
referencing==0.36.2
reportbug==12.0.0
requests==2.28.1
requests-toolbelt==0.10.1
rfc3986==1.5.0
rich==13.3.1
rpds-py==0.27.0
six==1.16.0
sniffio==1.2.0
sqlparse==0.5.3
typing_extensions==4.14.1
uritemplate==4.2.0
urllib3==1.26.12
wadllib==1.3.6
EOF

pip install -r /tmp/reqs.txt
```shell
cat requirements


pip install -r requirments.txt
```



## Test

```shell
python3 -c "import libzfs; print('Module installed successfully') ;print(libzfs.__doc__);import sys; print(sys.path)"
#OUTPUT:
## ---> Module installed successfully
## ---> None
## ---> ['', '/usr/lib/python311.zip', '/usr/lib/python3.11', '/usr/lib/python3.11/lib-dynload', '/usr/local/lib/python3.11/dist-packages', '/usr/lib/python3/dist-packages', '/usr/lib/python3.11/dist-packages']
```

[URL](https://installati.one/debian/12/)