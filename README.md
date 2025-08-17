
# Step1
`install Debian 12` with all configuration

# Step2
After boot OS install this packages

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

## Test

```shell
python3 -c "import libzfs; print('Module installed successfully') ;print(libzfs.__doc__)"
```

[URL](https://installati.one/debian/12/)