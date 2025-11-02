#!/usr/bin/env bash

# StoreX-CLI v5.9 - Final Version
# REVISED: Replaced the header with the new user-provided ASCII art.

# --- General Purpose Functions ---
confirm_action() {
    read -p "Are you sure you want to continue? (y/N): " response
    response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
    if [[ "$response" != "y" ]]; then
        echo "Action canceled."
        return 1
    fi
    return 0
}

check_dependency() {
    if ! command -v "$1" &> /dev/null && [ ! -x "/usr/sbin/$1" ] && [ ! -x "/sbin/$1" ]; then
        echo "Error: A required management tool ('$1') is not installed or not found."
        return 1
    fi
    return 0
}

# --- Internal Helper: Get OS Disk ---
_get_os_disk() {
    local os_partition=$(findmnt -n -o SOURCE --target /)
    if [ -n "$os_partition" ]; then
        lsblk -n -o PKNAME "$os_partition"
    fi
}

# --- Header and Help Text Functions ---
_print_header() {
    clear
    echo '███████╗████████╗ ██████╗ ██████╗ ███████╗██╗  ██╗      ██████╗██╗     ██╗'
    echo '██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝     ██╔════╝██║     ██║'
    echo '███████╗   ██║   ██║   ██║██████╔╝█████╗   ╚███╔╝█████╗██║     ██║     ██║'
    echo '╚════██║   ██║   ██║   ██║██╔══██╗██╔══╝   ██╔██╗╚════╝██║     ██║     ██║'
    echo '███████║   ██║   ╚██████╔╝██║  ██║███████╗██╔╝ ██╗     ╚██████╗███████╗██║'
    echo '╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝      ╚═════╝╚══════╝╚═╝'
    echo '┌────────────────────────┐'
    echo '│ Welcome to StoreX-CLI  │'
    echo '│ Family: NULL           │'
    echo '│ Copyright © 1404       │'
    echo '└────────────────────────┘'
    echo ""
}

_main_help() {
    echo "Available menus:"
    echo "  Disk      - Disk management commands"
    echo "  Pool      - Storage pool management commands"
    echo "  Hardware  - Hardware monitoring commands"
    echo "  Network   - Network management commands"
    echo "  Service   - System service management commands"
    echo "  System    - General system management commands"
    echo "  Help      - Show this help message"
    echo "  Exit      - Exit the CLI"
}

_disk_help() {
    echo "Available commands in 'Disk' menu:"
    echo "  All                  Show all data disks with WWN and Bus Location"
    echo "  Unused               Show unused/raw data disks"
    echo "  Info                 Show detailed info for physical identification"
    echo "  Help                 Show this help message"
    echo "  Back                 Return to the main menu"
}

_pool_help() {
    echo "Available commands in 'Pool' menu:"
    echo "  Pool List                           List all active pools"
    echo "  Pool Status <poolName>              Show status of a specific pool"
    echo "  Pool Import <poolName>              Import a detached pool"
    echo "  Pool Export <poolName>              Export an active pool"
    echo "  Pool Scrub <poolName>               Start data integrity check"
    echo "  Perf <pool> <interval> <count>      Monitor pool performance"
    echo "  Help                                Show this help message"
    echo "  Back                                Return to the main menu"
}

_hardware_help() {
    echo "Available commands in 'Hardware' menu:"
    echo "  Show Cpu             Monitor CPU usage for 5 seconds"
    echo "  Show Memory          Show memory usage in Gigabytes"
    echo "  Help                 Show this help message"
    echo "  Back                 Return to the main menu"
}

_network_help() {
    echo "Available commands in 'Network' menu:"
    echo "  Nic List                            List real network interfaces (Name and IP)"
    echo "  Nic Set <nic> [up|down]             Enable/disable a NIC"
    echo "  Nic Edit                            Edit an existing permanent IP via an interactive wizard"
    echo "  Gateway Get                         Show the default gateway IP"
    echo "  Gateway Set <ip>                    Set a temporary gateway"
    echo "  Help                                Show this help message"
    echo "  Back                                Return to the main menu"
}

_service_help(){
    echo "Available commands in 'Service' menu:"
    echo "  Network   [start|stop|restart|status]   Manage the Network service"
    echo "  Sharing   [start|stop|restart|status]   Manage the Sharing service"
    echo "  Ssh       [start|stop|restart|status]   Manage the SSH service"
    echo "  Webserver [start|stop|restart|status]   Manage the Web Server service"
    echo "  Help                                    Show this help message"
    echo "  Back                                    Return to the main menu"
}

_system_help() {
    echo "Available commands in 'System' menu:"
    echo "  Password Set Cli        Change password for the current user"
    echo "  Ping <ip_or_host>       Test network connectivity"
    echo "  Reboot                  Reboot the server"
    echo "  Shutdown                Shutdown the server"
    echo "  Time [status|set|...]   Manage system time"
    echo "  Uptime                  Show system uptime"
    echo "  Help                    Show this help message"
    echo "  Back                    Return to the main menu"
}

# --- Internal Network Helper Function ---
_apply_permanent_ip() {
    local iface=$1; local ipaddr=$2; local netmask=$3; local gateway=$4
    local config_block="
auto $iface
iface $iface inet static
    address $ipaddr
    netmask $netmask"
    if [ -n "$gateway" ]; then config_block="$config_block
    gateway $gateway"; fi
    echo "The final configuration will be:"; echo "-----------------------------------"; echo "$config_block"; echo "-----------------------------------"
    if confirm_action; then
        sudo cp /etc/network/interfaces /etc/network/interfaces.backup.$(date +%F-%T); echo "Backup of /etc/network/interfaces created."
        sudo sed -i -E "/auto $iface|iface $iface/,/^\S/ s/^/# /" /etc/network/interfaces
        echo "$config_block" | sudo tee -a /etc/network/interfaces > /dev/null; echo "Configuration file updated."
        echo "Restarting the main networking service to apply all changes..."
        if sudo systemctl restart networking; then echo "Networking service restarted successfully."; else echo "Error restarting the networking service. Please check system logs."; fi
    fi
}

# --- Menu Functions ---

disk_menu() {
    clear; _disk_help
    while true; do
        read -p "disk>> " -a cmd_arr
        local cmd=${cmd_arr[0]}; cmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]')
        local os_disk=$(_get_os_disk)
        
        case "$cmd" in
            all)
                check_dependency lsscsi || continue
                echo "--> Showing all data disks (excluding OS disk '$os_disk'):"
                local data_disks=$(lsblk -d -n -o NAME | grep -v "$os_disk")
                if [ -z "$data_disks" ]; then echo "No data disks found."; continue; fi
                
                printf "%-10s %-15s %s\n" "DEVICE" "BUS LOCATION" "WWN"
                printf "%.0s-" {1..60}; echo ""

                for disk in $data_disks; do
                    local wwn=$(lsblk -d -n -o WWN "/dev/$disk")
                    local bus_info=$(lsscsi | grep "/dev/$disk" | awk '{print $1}')
                    printf "%-10s %-15s %s\n" "$disk" "$bus_info" "$wwn"
                done
                ;;
            unused)
                echo "--> Searching for unused/raw data disks..."
                all_disks=$(lsblk -d -n -o NAME | grep -v "$os_disk")
                used_disks=$(lsblk -n -o PKNAME | sort -u)
                free_disks_list=""
                for disk in $all_disks; do
                    if ! echo "$used_disks" | grep -qw "$disk"; then free_disks_list+="$disk "; fi
                done
                if [ -n "$free_disks_list" ]; then
                    echo "Found free/raw disks: $free_disks_list"
                else
                    echo "No free/raw data disks found."
                fi
                ;;
            info)
                check_dependency smartctl || continue; check_dependency lshw || continue; check_dependency lsscsi || continue
                echo "--> Detailed info for all data disks:"
                local data_disks=$(lsblk -d -n -o NAME | grep -v "$os_disk")
                if [ -z "$data_disks" ]; then echo "No data disks found."; continue; fi

                for disk in $data_disks; do
                    echo "--- Info for /dev/$disk ---"
                    local hw_path=$(sudo lshw -class disk -short | grep "/dev/$disk" | awk '{print $1}')
                    local bus_info=$(lsscsi | grep "/dev/$disk" | awk '{print $1}')
                    local temp=$(sudo smartctl -A "/dev/$disk" | grep "Temperature_Celsius" | awk '{print $10}')
                    
                    echo "H/W Path:        $hw_path"
                    echo "Bus Location:    $bus_info"
                    sudo smartctl -i "/dev/$disk" | grep -E "Device Model|Serial Number|User Capacity"
                    if [ -n "$temp" ]; then
                        echo "Temperature:     ${temp}°C"
                    fi
                    echo ""
                done
                ;;
            help) _disk_help ;;
            back) return ;;
            clear) clear; _disk_help ;;
            exit) exit 0 ;;
            *) [[ -n "$cmd" ]] && echo "Unknown command: '$cmd'." ;;
        esac
    done
}

pool_menu() {
    check_dependency zpool || return; clear; _pool_help
    while true; do
        read -p "pool>> " -a cmd_arr
        local cmd=${cmd_arr[0]}; local arg1=${cmd_arr[1]}; cmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]')
        case "$cmd" in
            pool)
                case "$arg1" in
                    list) sudo zpool list ;; 
                    status) sudo zpool status "${cmd_arr[@]:2}" ;; 
                    import) sudo zpool import "${cmd_arr[@]:2}" ;;
                    export) confirm_action && sudo zpool export "${cmd_arr[@]:2}" ;; 
                    scrub) sudo zpool scrub "${cmd_arr[@]:2}" ;;
                    *) echo "Error: Unknown subcommand." ;;
                esac ;;
            perf) check_dependency iostat && zpool iostat -v "${cmd_arr[@]:1}" ;;
            help) _pool_help ;; back) return ;; clear) clear; _pool_help ;; exit) exit 0 ;;
            *) [[ -n "$cmd" ]] && echo "Error: Unknown command '$cmd'. Use 'pool <subcommand>'. Type 'help' for details." ;;
        esac
    done
}

hardware_menu() {
    clear; _hardware_help
    while true; do
        read -p "hardware>> " -a cmd_arr
        local cmd=${cmd_arr[0]}; local arg1=${cmd_arr[1]}; cmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]')
        case "$cmd" in
            show)
                case "$arg1" in
                    cpu) check_dependency mpstat && mpstat 1 5 ;;
                    memory) free -g ;;
                    *) _hardware_help ;;
                esac ;;
            help) _hardware_help ;; back) return ;; clear) clear; _hardware_help ;; exit) exit 0 ;;
            *) [[ -n "$cmd" ]] && echo "Unknown command: '$cmd'." ;;
        esac
    done
}

network_menu() {
    clear; _network_help
    while true; do
        read -p "network>> " -a cmd_arr; local cmd=${cmd_arr[0]}; local arg1=${cmd_arr[1]}; cmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]')
        case "$cmd" in
            nic)
                case "$arg1" in
                    list) echo "--> Listing Interfaces and IP Addresses:"; ip -o -4 addr show | grep -v ' lo ' | awk '{print "    " $2 ":\t" $4}' ;;
                    set) sudo ip link set "${cmd_arr[2]}" "${cmd_arr[3]}" ;;
                    edit)
                        echo "--- Edit Permanent IP Wizard ---"; read -p "Enter interface name to edit (e.g., enp4s0): " iface; if [ -z "$iface" ]; then echo "Canceled."; continue; fi
                        local current_ip=$(awk "/iface $iface inet static/,/^\S/" /etc/network/interfaces | grep 'address' | awk '{print $2}' | tail -n 1)
                        local current_mask=$(awk "/iface $iface inet static/,/^\S/" /etc/network/interfaces | grep 'netmask' | awk '{print $2}' | tail -n 1)
                        local current_gw=$(awk "/iface $iface inet static/,/^\S/" /etc/network/interfaces | grep 'gateway' | awk '{print $2}' | tail -n 1)
                        read -p "IP Address [$current_ip]: " new_ip; read -p "Netmask [$current_mask]: " new_mask; read -p "Gateway [$current_gw]: " new_gw
                        new_ip=${new_ip:-$current_ip}; new_mask=${new_mask:-$current_mask}; new_gw=${new_gw:-$current_gw}
                        if [ -z "$new_ip" ] || [ -z "$new_mask" ]; then echo "IP and netmask cannot be empty. Canceled."; continue; fi
                        _apply_permanent_ip "$iface" "$new_ip" "$new_mask" "$new_gw" ;;
                    *) _network_help ;;
                esac ;;
            gateway)
                case "$arg1" in
                    get) ip route | grep default | awk '{print "Default Gateway: " $3}' ;;
                    set) echo "Note: This sets a temporary gateway."; sudo ip route add default via "${cmd_arr[2]}" ;; 
                    *) _network_help ;;
                esac ;;
            help) _network_help ;; back) return ;; clear) clear; _network_help ;; exit) exit 0 ;;
            *) [[ -n "$cmd" ]] && echo "Unknown command: '$cmd'." ;;
        esac
    done
}

service_menu() {
    clear; _service_help
    while true; do
        read -p "service>> " -a cmd_arr; local cmd=${cmd_arr[0]}; local action=${cmd_arr[1]}; cmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]'); action=$(echo "$action" | tr '[:upper:]' '[:lower:]')
        local service_name=""; case "$cmd" in network) service_name="networking" ;; sharing) service_name="smbd" ;; ssh) service_name="ssh" ;; webserver) service_name="nginx" ;; help) _service_help; continue ;; back) return ;; clear) clear; _service_help; continue ;; exit) exit 0 ;; *) [[ -n "$cmd" ]] && echo "Unknown service: '$cmd'."; continue ;; esac
        if [[ "$action" == "start" || "$action" == "stop" || "$action" == "restart" ]]; then sudo systemctl "$action" "$service_name"; elif [[ "$action" == "status" ]]; then local status=$(systemctl is-active "$service_name"); echo "--> Status for '$cmd' service: $status"; else echo "Invalid action. Use [start|stop|restart|status]."; fi
    done
}

system_menu() {
    clear; _system_help
    while true; do
        read -p "system>> " -a cmd_arr; local cmd=${cmd_arr[0]}; local arg1=${cmd_arr[1]}; local arg2=${cmd_arr[2]}; cmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]')
        case "$cmd" in
            password)
                if [[ "$arg1" == "set" && "$arg2" == "cli" ]]; then
                    echo "WARNING: You are about to change the password for the current CLI user ($(whoami))."
                    if confirm_action; then passwd; fi
                else _system_help; fi ;;
            ping) ping -c 4 "$arg1" ;;
            reboot) confirm_action && sudo reboot ;;
            shutdown) confirm_action && sudo shutdown now ;;
            time)
                local action=${cmd_arr[1]}
                if [[ -z "$action" || "$action" == "status" ]]; then
                    timedatectl status | grep "Local time" | sed 's/^[[:space:]]*Local time:/System Time:/'
                elif [[ "$action" == "set" ]]; then
                    read -p "Enter new time [YYYY-MM-DD HH:MM:SS]: " new_time
                    if [[ -n "$new_time" ]]; then sudo timedatectl set-time "$new_time"; else echo "Canceled."; fi
                else sudo timedatectl "${cmd_arr[@]:1}"; fi
                ;;
            uptime)
                uptime -p
                ;;
            help) _system_help ;; back) return ;; clear) clear; _system_help ;; exit) exit 0 ;;
            *) [[ -n "$cmd" ]] && echo "Unknown command: '$cmd'." ;;
        esac
    done
}


# --- Main Menu ---
main_menu() {
    _print_header
    _main_help
    while true; do
        read -p "storex-CLI>> " choice; choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')
        case "$choice" in
            disk) disk_menu ;; pool) pool_menu ;; hardware) hardware_menu ;;
            network) network_menu ;; service) service_menu ;; system) system_menu ;;
            help) clear; _print_header; _main_help ;;
            clear) clear; _print_header; _main_help ;;
            exit) echo "Exiting."; exit 0 ;;
            *) if [[ -n "$choice" ]]; then echo "Unknown menu: '$choice'."; fi ;;
        esac
    done
}

# --- Script Start ---
main_menu
