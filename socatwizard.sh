#!/bin/bash

# ====================================================
# System Requirements: CentOS 7+, Debian 9+, Ubuntu 16+
# Description: Enhanced Socat installation and configuration script
# Features: Better error handling, logging, security, and management
# ====================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors and formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/log/socat-setup.log"
readonly CONFIG_DIR="/etc/socat"
readonly CONFIG_FILE="/etc/socat/socat.conf"
readonly TUNNEL_CONFIG_DIR="/etc/socat/tunnels"
readonly SERVICE_NAME="socat-tunnel"
readonly SOCAT_USER="socat"

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

info() { log "INFO" "$@"; }
warn() { log "WARN" "${YELLOW}$*${NC}"; }
error() { log "ERROR" "${RED}$*${NC}"; }
success() { log "SUCCESS" "${GREEN}$*${NC}"; }

# Error handling
trap 'error "Script failed at line $LINENO"' ERR

# Display main menu
show_main_menu() {
    clear
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}        Socat Tunnel Manager${NC}"
    echo -e "${GREEN}===========================================${NC}"
    echo
    echo "Please select an option:"
    echo
    echo "1) Install Socat"
    echo "2) Configure New Tunnel"
    echo "3) Show All Tunnels"
    echo "4) Remove Specific Tunnel"
    echo "5) Restart Service"
    echo "6) Stop Service"
    echo "7) Uninstall & Remove All Config"
    echo "8) Exit"
    echo
    echo -e "${BLUE}Current Status:${NC}"
    if command -v socat &>/dev/null; then
        echo -e "${GREEN}✓ Socat is installed${NC}"
    else
        echo -e "${RED}✗ Socat is not installed${NC}"
    fi
    
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo -e "${GREEN}✓ Tunnel service is running${NC}"
    else
        echo -e "${RED}✗ Tunnel service is not running${NC}"
    fi
    
    # Show tunnel count
    local tunnels=($(list_tunnels))
    if [[ ${#tunnels[@]} -gt 0 ]]; then
        echo -e "${GREEN}✓ ${#tunnels[@]} tunnel(s) configured${NC}"
        for tunnel in "${tunnels[@]}"; do
            local config_file="$TUNNEL_CONFIG_DIR/${tunnel}.conf"
            if [[ -f "$config_file" ]]; then
                source "$config_file"
                echo -e "${BLUE}   ${tunnel}: localhost:${LOCAL_PORT} -> ${REMOTE_IP}:${REMOTE_PORT}${NC}"
            fi
        done
    else
        echo -e "${RED}✗ No tunnels configured${NC}"
    fi
    echo
}}"
    echo -e "${GREEN}        Socat Tunnel Manager${NC}"
    echo -e "${GREEN}===========================================${NC}"
    echo
    echo "Please select an option:"
    echo
    echo "1) Install Socat"
    echo "2) Configure Tunnel"
    echo "3) Show Status"
    echo "4) Restart Service"
    echo "5) Stop Service"
    echo "6) Uninstall & Remove Config"
    echo "7) Exit"
    echo
    echo -e "${BLUE}Current Status:${NC}"
    if command -v socat &>/dev/null; then
        echo -e "${GREEN}✓ Socat is installed${NC}"
    else
        echo -e "${RED}✗ Socat is not installed${NC}"
    fi
    
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo -e "${GREEN}✓ Tunnel service is running${NC}"
    else
        echo -e "${RED}✗ Tunnel service is not running${NC}"
    fi
    
    if [[ -f "$CONFIG_FILE" ]]; then
        echo -e "${GREEN}✓ Configuration exists${NC}"
        local local_port=$(grep "LOCAL_PORT=" "$CONFIG_FILE" | cut -d'=' -f2)
        local remote_ip=$(grep "REMOTE_IP=" "$CONFIG_FILE" | cut -d'=' -f2)
        local remote_port=$(grep "REMOTE_PORT=" "$CONFIG_FILE" | cut -d'=' -f2)
        echo -e "${BLUE}   Current tunnel: localhost:${local_port} -> ${remote_ip}:${remote_port}${NC}"
    else
        echo -e "${RED}✗ No configuration found${NC}"
    fi
    echo
}

# Handle menu selection
handle_menu_selection() {
    local choice
    while true; do
        show_main_menu
        read -p "Enter your choice [1-7]: " choice
        
        case $choice in
            1)
                echo
                info "Installing Socat..."
                install_socat
                echo
                read -p "Press Enter to continue..."
                ;;
            2)
                echo
                setup_config_dir
                create_socat_user
                interactive_configure
                echo
                read -p "Press Enter to continue..."
                ;;
            3)
                echo
                show_tunnel_info
                echo
                read -p "Press Enter to continue..."
                ;;
            4)
                echo
                if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
                    systemctl restart "$SERVICE_NAME"
                    success "Service restarted"
                else
                    warn "Service is not running. Use option 2 to configure first."
                fi
                echo
                read -p "Press Enter to continue..."
                ;;
            5)
                echo
                if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
                    systemctl stop "$SERVICE_NAME"
                    success "Service stopped"
                else
                    warn "Service is not running"
                fi
                echo
                read -p "Press Enter to continue..."
                ;;
            6)
                echo
                read -p "Are you sure you want to uninstall? (y/N): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    uninstall_socat
                else
                    info "Uninstall cancelled"
                fi
                echo
                read -p "Press Enter to continue..."
                ;;
            7)
                echo
                success "Goodbye!"
                exit 0
                ;;
            *)
                echo
                error "Invalid choice. Please select 1-7."
                echo
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root!"
        exit 1
    fi
}

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
    
    info "Detected OS: $OS $VER"
}

# Validate input
validate_port() {
    local port=$1
    if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        error "Invalid port: $port. Must be between 1-65535."
        return 1
    fi
}

validate_ip() {
    local ip=$1
    if ! [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        error "Invalid IP address: $ip"
        return 1
    fi
}

# Generate tunnel name from parameters
generate_tunnel_name() {
    local local_port=$1
    local remote_ip=$2
    local remote_port=$3
    echo "tunnel_${local_port}_to_${remote_ip//./_}_${remote_port}"
}

# List all configured tunnels
list_tunnels() {
    local tunnels=()
    
    if [[ -d "$TUNNEL_CONFIG_DIR" ]]; then
        for config_file in "$TUNNEL_CONFIG_DIR"/*.conf; do
            [[ -f "$config_file" ]] || continue
            tunnels+=("$(basename "$config_file" .conf)")
        done
    fi
    
    echo "${tunnels[@]}"
}

# Get tunnel configuration
get_tunnel_config() {
    local tunnel_name=$1
    local config_file="$TUNNEL_CONFIG_DIR/${tunnel_name}.conf"
    
    if [[ -f "$config_file" ]]; then
        source "$config_file"
        echo "Local Port: $LOCAL_PORT"
        echo "Remote IP: $REMOTE_IP"
        echo "Remote Port: $REMOTE_PORT"
        echo "Protocol: $PROTOCOL"
        echo "Created: $CREATED"
    else
        return 1
    fi
}

# Check if tunnel exists
tunnel_exists() {
    local tunnel_name=$1
    [[ -f "$TUNNEL_CONFIG_DIR/${tunnel_name}.conf" ]]
}

# Remove specific tunnel
remove_tunnel() {
    local tunnel_name=$1
    local config_file="$TUNNEL_CONFIG_DIR/${tunnel_name}.conf"
    
    if [[ ! -f "$config_file" ]]; then
        error "Tunnel '$tunnel_name' not found"
        return 1
    fi
    
    # Load tunnel config to get the port for cleanup
    source "$config_file"
    
    # Stop specific tunnel processes
    local pid_files=("/var/run/socat-tunnel-${tunnel_name}-tcp.pid" "/var/run/socat-tunnel-${tunnel_name}-udp.pid")
    for pid_file in "${pid_files[@]}"; do
        if [[ -f "$pid_file" ]]; then
            kill "$(cat "$pid_file")" 2>/dev/null || true
            rm -f "$pid_file"
        fi
    done
    
    # Kill any remaining processes for this tunnel
    pkill -f "socat.*LISTEN:${LOCAL_PORT}" || true
    
    # Remove config file
    rm -f "$config_file"
    
    # Restart service to reload remaining tunnels
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl reload "$SERVICE_NAME" 2>/dev/null || systemctl restart "$SERVICE_NAME"
    fi
    
    success "Tunnel '$tunnel_name' removed successfully"
}

# Interactive tunnel removal
interactive_remove_tunnel() {
    local tunnels=($(list_tunnels))
    
    if [[ ${#tunnels[@]} -eq 0 ]]; then
        warn "No tunnels configured"
        return 1
    fi
    
    echo -e "${GREEN}Remove Tunnel${NC}"
    echo "=============="
    echo
    echo "Configured tunnels:"
    echo
    
    for i in "${!tunnels[@]}"; do
        echo "$((i+1))) ${tunnels[i]}"
        echo "   $(get_tunnel_config "${tunnels[i]}" | head -4 | tr '\n' ' ')"
        echo
    done
    
    echo "$((${#tunnels[@]}+1))) Cancel"
    echo
    
    while true; do
        read -p "Select tunnel to remove [1-$((${#tunnels[@]}+1))]: " choice
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -ge 1 ]] && [[ "$choice" -le $((${#tunnels[@]}+1)) ]]; then
            if [[ "$choice" -eq $((${#tunnels[@]}+1)) ]]; then
                info "Removal cancelled"
                return 0
            fi
            
            local selected_tunnel="${tunnels[$((choice-1))]}"
            echo
            echo "Tunnel details:"
            get_tunnel_config "$selected_tunnel"
            echo
            
            read -p "Are you sure you want to remove this tunnel? (y/N): " confirm
            if [[ "$confirm" =~ ^[Yy]$ ]]; then
                remove_tunnel "$selected_tunnel"
            else
                info "Removal cancelled"
            fi
            return 0
        else
            echo "Invalid choice. Please select a number between 1 and $((${#tunnels[@]}+1))."
        fi
    done
}

# Create socat user
create_socat_user() {
    if ! id "$SOCAT_USER" &>/dev/null; then
        info "Creating socat user..."
        useradd -r -s /bin/false -d /nonexistent "$SOCAT_USER"
        success "Created socat user"
    fi
}

# Install socat
install_socat() {
    info "Installing socat..."
    
    case "$OS" in
        centos|rhel|fedora)
            if command -v dnf &>/dev/null; then
                dnf install -y socat
            else
                yum install -y socat
            fi
            ;;
        debian|ubuntu)
            apt-get update
            apt-get install -y socat
            ;;
        *)
            error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    if command -v socat &>/dev/null; then
        success "Socat installed successfully"
    else
        error "Socat installation failed"
        exit 1
    fi
}

# Create configuration directory
setup_config_dir() {
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$TUNNEL_CONFIG_DIR"
    mkdir -p /var/log/socat
    chown "$SOCAT_USER:$SOCAT_USER" /var/log/socat
}

# Generate systemd service for all tunnels
create_systemd_service() {
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Socat Tunnel Service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=forking
User=${SOCAT_USER}
Group=${SOCAT_USER}
Restart=always
RestartSec=1
ExecStart=/usr/local/bin/socat-tunnel-start.sh
ExecStop=/usr/local/bin/socat-tunnel-stop.sh
ExecReload=/usr/local/bin/socat-tunnel-reload.sh
PIDFile=/var/run/socat-tunnel.pid

[Install]
WantedBy=multi-user.target
EOF

    # Create start script
    cat > "/usr/local/bin/socat-tunnel-start.sh" << 'EOF'
#!/bin/bash
set -e

TUNNEL_CONFIG_DIR="/etc/socat/tunnels"
PID_DIR="/var/run"

# Start all configured tunnels
for config_file in "$TUNNEL_CONFIG_DIR"/*.conf; do
    [[ -f "$config_file" ]] || continue
    
    # Load configuration
    source "$config_file"
    
    # Create unique PID file name
    tunnel_name=$(basename "$config_file" .conf)
    
    # Start tunnel(s)
    if [[ "$PROTOCOL" == "tcp" || "$PROTOCOL" == "both" ]]; then
        socat TCP4-LISTEN:$LOCAL_PORT,reuseaddr,fork TCP4:$REMOTE_IP:$REMOTE_PORT &
        echo $! > "$PID_DIR/socat-tunnel-${tunnel_name}-tcp.pid"
    fi

    if [[ "$PROTOCOL" == "udp" || "$PROTOCOL" == "both" ]]; then
        socat -T 600 UDP4-LISTEN:$LOCAL_PORT,reuseaddr,fork UDP4:$REMOTE_IP:$REMOTE_PORT &
        echo $! > "$PID_DIR/socat-tunnel-${tunnel_name}-udp.pid"
    fi
done

# Create main PID file
echo $ > "$PID_DIR/socat-tunnel.pid"
EOF

    # Create stop script
    cat > "/usr/local/bin/socat-tunnel-stop.sh" << 'EOF'
#!/bin/bash

PID_DIR="/var/run"

# Kill all tunnel processes
for pidfile in "$PID_DIR"/socat-tunnel-*.pid; do
    if [[ -f "$pidfile" ]]; then
        kill $(cat "$pidfile") 2>/dev/null || true
        rm -f "$pidfile"
    fi
done

# Kill any remaining socat processes
pkill -f "socat.*LISTEN" || true
EOF

    # Create reload script
    cat > "/usr/local/bin/socat-tunnel-reload.sh" << 'EOF'
#!/bin/bash

# Stop all tunnels
/usr/local/bin/socat-tunnel-stop.sh

# Start all tunnels
/usr/local/bin/socat-tunnel-start.sh
EOF

    chmod +x "/usr/local/bin/socat-tunnel-start.sh"
    chmod +x "/usr/local/bin/socat-tunnel-stop.sh"
    chmod +x "/usr/local/bin/socat-tunnel-reload.sh"
    
    systemctl daemon-reload
    success "Systemd service created"
}

# Configure socat
configure_socat() {
    local local_port=$1
    local remote_ip=$2
    local remote_port=$3
    local protocol=${4:-both}
    
    info "Configuring socat tunnel..."
    
    # Validate inputs
    validate_port "$local_port"
    validate_ip "$remote_ip"
    validate_port "$remote_port"
    check_port_usage "$local_port"
    
    # Generate tunnel name
    local tunnel_name=$(generate_tunnel_name "$local_port" "$remote_ip" "$remote_port")
    local config_file="$TUNNEL_CONFIG_DIR/${tunnel_name}.conf"
    
    # Check if tunnel already exists
    if [[ -f "$config_file" ]]; then
        error "A tunnel with these parameters already exists: $tunnel_name"
        return 1
    fi
    
    # Create tunnel configuration
    cat > "$config_file" << EOF
# Socat tunnel configuration
LOCAL_PORT=$local_port
REMOTE_IP=$remote_ip
REMOTE_PORT=$remote_port
PROTOCOL=$protocol
CREATED=$(date)
EOF
    
    # Create or update systemd service
    create_systemd_service
    
    # Enable and start/reload service
    systemctl enable "$SERVICE_NAME"
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl reload "$SERVICE_NAME" 2>/dev/null || systemctl restart "$SERVICE_NAME"
    else
        systemctl start "$SERVICE_NAME"
    fi
    
    success "Tunnel '$tunnel_name' configured and started"
    show_tunnel_info "$tunnel_name"
}

# Show tunnel information
show_tunnel_info() {
    local specific_tunnel=$1
    
    if [[ -n "$specific_tunnel" ]]; then
        # Show specific tunnel info
        local config_file="$TUNNEL_CONFIG_DIR/${specific_tunnel}.conf"
        if [[ -f "$config_file" ]]; then
            info "Tunnel '$specific_tunnel' configuration:"
            get_tunnel_config "$specific_tunnel"
        else
            error "Tunnel '$specific_tunnel' not found"
            return 1
        fi
    else
        # Show all tunnels
        local tunnels=($(list_tunnels))
        
        if [[ ${#tunnels[@]} -eq 0 ]]; then
            warn "No tunnels configured"
            return 1
        fi
        
        info "Configured tunnels:"
        echo "==================="
        
        for tunnel in "${tunnels[@]}"; do
            echo
            echo "Tunnel: $tunnel"
            echo "$(get_tunnel_config "$tunnel" | sed 's/^/  /')"
        done
        
        echo
        info "Service status:"
        systemctl status "$SERVICE_NAME" --no-pager -l || true
        
        echo
        info "Active connections:"
        for tunnel in "${tunnels[@]}"; do
            local config_file="$TUNNEL_CONFIG_DIR/${tunnel}.conf"
            if [[ -f "$config_file" ]]; then
                source "$config_file"
                echo "Port $LOCAL_PORT:"
                netstat -tuln | grep ":$LOCAL_PORT" | sed 's/^/  /' || echo "  No active connections"
            fi
        done
    fi
}

# Interactive configuration
interactive_configure() {
    echo -e "${GREEN}Socat Tunnel Configuration${NC}"
    echo "=================================="
    echo
    
    # Check if socat is installed
    if ! command -v socat &>/dev/null; then
        error "Socat is not installed. Please install it first (option 1 from main menu)."
        return 1
    fi
    
    local local_port remote_ip remote_port protocol
    
    # Get local port
    while true; do
        read -p "Enter local port (1-65535): " local_port
        if validate_port "$local_port" && check_port_usage "$local_port"; then
            break
        fi
        echo "Please enter a valid, unused port number."
    done
    
    # Get remote IP
    while true; do
        read -p "Enter remote IP address: " remote_ip
        if validate_ip "$remote_ip"; then
            break
        fi
        echo "Please enter a valid IP address."
    done
    
    # Get remote port
    while true; do
        read -p "Enter remote port (1-65535): " remote_port
        if validate_port "$remote_port"; then
            break
        fi
        echo "Please enter a valid port number."
    done
    
    # Get protocol
    echo
    echo "Select protocol:"
    echo "1) TCP only"
    echo "2) UDP only"
    echo "3) Both TCP and UDP"
    
    while true; do
        read -p "Enter choice [1-3] (default: 3): " proto_choice
        proto_choice=${proto_choice:-3}
        
        case $proto_choice in
            1) protocol="tcp"; break ;;
            2) protocol="udp"; break ;;
            3) protocol="both"; break ;;
            *) echo "Please enter 1, 2, or 3." ;;
        esac
    done
    
    echo
    echo "Configuration Summary:"
    echo "====================="
    echo "Local Port: $local_port"
    echo "Remote IP: $remote_ip"
    echo "Remote Port: $remote_port"
    echo "Protocol: $protocol"
    echo
    
    read -p "Proceed with this configuration? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        configure_socat "$local_port" "$remote_ip" "$remote_port" "$protocol"
    else
        warn "Configuration cancelled."
    fi
}

# Uninstall function
uninstall_socat() {
    info "Uninstalling socat tunnel..."
    
    # Stop and disable service
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    
    # Remove files
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    rm -f "/usr/local/bin/socat-tunnel-start.sh"
    rm -f "/usr/local/bin/socat-tunnel-stop.sh"
    rm -f "$CONFIG_FILE"
    rm -rf "$(dirname "$CONFIG_FILE")"
    rm -f /var/run/socat-tunnel*.pid
    
    # Remove user
    userdel "$SOCAT_USER" 2>/dev/null || true
    
    systemctl daemon-reload
    success "Socat tunnel uninstalled"
}

# Main function
main() {
    local action=""
    local local_port=""
    local remote_ip=""
    local remote_port=""
    local protocol="both"
    
    # Setup logging
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    
    check_root
    detect_os
    
    # If no arguments provided, show interactive menu
    if [[ $# -eq 0 ]]; then
        handle_menu_selection
        return
    fi
    
    # Parse arguments for command-line usage
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                echo "Usage: $0 [OPTIONS] or run without arguments for interactive menu"
                echo
                echo "Command-line options:"
                echo "  -i, --install           Install socat only"
                echo "  -c, --configure         Configure socat tunnel"
                echo "  -s, --status           Show tunnel status"
                echo "  -r, --restart          Restart tunnel service"
                echo "  -t, --stop             Stop tunnel service"
                echo "  -u, --uninstall        Uninstall socat and remove configuration"
                echo "  --local-port PORT      Local port to listen on"
                echo "  --remote-port PORT     Remote port to connect to"
                echo "  --remote-ip IP         Remote IP address"
                echo "  --protocol PROTO       Protocol (tcp, udp, both) [default: both]"
                echo
                echo "Examples:"
                echo "  $0 --configure --local-port 8080 --remote-port 80 --remote-ip 192.168.1.100"
                echo "  $0 --status"
                echo "  $0 --uninstall"
                echo
                echo "For interactive menu, run without arguments: $0"
                exit 0
                ;;
            -i|--install)
                action="install"
                shift
                ;;
            -c|--configure)
                action="configure"
                shift
                ;;
            -s|--status)
                action="status"
                shift
                ;;
            -r|--restart)
                action="restart"
                shift
                ;;
            -t|--stop)
                action="stop"
                shift
                ;;
            -u|--uninstall)
                action="uninstall"
                shift
                ;;
            --local-port)
                local_port="$2"
                shift 2
                ;;
            --remote-ip)
                remote_ip="$2"
                shift 2
                ;;
            --remote-port)
                remote_port="$2"
                shift 2
                ;;
            --protocol)
                protocol="$2"
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                echo "Use -h or --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Execute command-line actions
    case "$action" in
        install)
            install_socat
            ;;
        configure)
            if [[ -n "$local_port" && -n "$remote_ip" && -n "$remote_port" ]]; then
                setup_config_dir
                create_socat_user
                configure_socat "$local_port" "$remote_ip" "$remote_port" "$protocol"
            else
                error "Missing required parameters for configure. Use --local-port, --remote-ip, and --remote-port"
                exit 1
            fi
            ;;
        status)
            show_tunnel_info
            ;;
        restart)
            systemctl restart "$SERVICE_NAME"
            success "Service restarted"
            ;;
        stop)
            systemctl stop "$SERVICE_NAME"
            success "Service stopped"
            ;;
        uninstall)
            uninstall_socat
            ;;
        *)
            error "No action specified. Use -h for help or run without arguments for interactive menu."
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
