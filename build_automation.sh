#!/bin/bash

# ============================================================================
# Build Automation Script
# ============================================================================
# This script automates the build, generate, deploy, and install workflow
# based on a configuration file.
#
# Usage: ./build_automation.sh -c <config_file> [-u] [-b] [-g] [-d] [-i] [-h]
#
# Options:
#   -c <config_file>  Path to configuration file (required)
#   -u                Update APP_ROOT in AppConfig.sh
#   -b                Build (compile HW or SW based on config)
#   -g                Generate deployment package
#   -d                Deploy to setup
#   -i                Install on setup
#   -a                Execute all steps (update, build, generate, deploy, install)
#   -h                Show this help message
# ============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Script variables
CONFIG_FILE=""
DO_UPDATE=false
DO_BUILD=false
DO_GENERATE=false
DO_DEPLOY=false
DO_INSTALL=false

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

print_command() {
    echo -e "${MAGENTA}[COMMAND]${NC} (from: $PWD)"
    echo -e "${MAGENTA}[COMMAND]${NC} $1"
    # Also print a plain, easy-to-read shell command line for tools and UIs
    echo -e "\u2192 $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 -c <config_file> [-u] [-b] [-g] [-d] [-i] [-a] [-h]

Options:
  -c <config_file>  Path to configuration file (required)
  -u                Update APP_ROOT in AppConfig.sh
  -b                Build (compile HW or SW based on config)
  -g                Generate deployment package
  -d                Deploy to setup
  -i                Install on setup
  -a                Execute all steps (update, build, generate, deploy, install)
  -h                Show this help message

Examples:
  # Update APP_ROOT and build only
  $0 -c build_config.cfg -u -b

  # Generate and deploy
  $0 -c build_config.cfg -g -d

  # Execute all steps
  $0 -c build_config.cfg -a
EOF
}

# Parse command line arguments
while getopts "c:ubgdiah" opt; do
    case $opt in
        c) CONFIG_FILE="$OPTARG" ;;
        u) DO_UPDATE=true ;;
        b) DO_BUILD=true ;;
        g) DO_GENERATE=true ;;
        d) DO_DEPLOY=true ;;
        i) DO_INSTALL=true ;;
        a) 
            DO_UPDATE=true
            DO_BUILD=true
            DO_GENERATE=true
            DO_DEPLOY=true
            DO_INSTALL=true
            ;;
        h) show_usage; exit 0 ;;
        *) show_usage; exit 1 ;;
    esac
done

# Check if config file is provided, use default if not
if [ -z "$CONFIG_FILE" ]; then
    # Use default config file
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    CONFIG_FILE="$SCRIPT_DIR/build_config.cfg"
    print_info "No config file specified, using default: $CONFIG_FILE"
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Load configuration file
print_info "Loading configuration from: $CONFIG_FILE"
source "$CONFIG_FILE"

# Validate required variables
if [ -z "$APP_ROOT" ]; then
    print_error "APP_ROOT not defined in config file"
    exit 1
fi

if [ -z "$PROJECT_NAME" ]; then
    print_error "PROJECT_NAME not defined in config file"
    exit 1
fi

if [ -z "$ENV_PATH" ]; then
    print_error "ENV_PATH not defined in config file"
    exit 1
fi

print_success "Configuration loaded successfully"
print_info "APP_ROOT: $APP_ROOT"
print_info "PROJECT_NAME: $PROJECT_NAME"
print_info "BUILD_TYPE: $BUILD_TYPE"
print_info "ENV_PATH: $ENV_PATH"

# Check if at least one action is selected
if [ "$DO_UPDATE" = false ] && [ "$DO_BUILD" = false ] && [ "$DO_GENERATE" = false ] && [ "$DO_DEPLOY" = false ] && [ "$DO_INSTALL" = false ]; then
    print_warning "No action selected. Use -u, -b, -g, -d, -i, or -a"
    show_usage
    exit 1
fi

# ============================================================================
# Step 1: Update APP_ROOT
# ============================================================================
update_app_root() {
    print_step "STEP 1: Updating APP_ROOT in AppConfig.sh"
    
    local appconfig_path="$ENV_PATH/ME.Develop/BuildSys/AppConfig.sh"
    local epgconfig_path="$ENV_PATH/ME.Develop/BuildSys/EpgConfig.sh"
    
    if [ ! -f "$appconfig_path" ]; then
        print_error "AppConfig.sh not found at: $appconfig_path"
        return 1
    fi
    
    # Backup the original file
    cp "$appconfig_path" "${appconfig_path}.backup.$(date +%Y%m%d_%H%M%S)"
    print_info "Created backup of AppConfig.sh"
    
    # Update APP_ROOT using sed
    sed -i "s|setenv APP_ROOT .*|setenv APP_ROOT $APP_ROOT|g" "$appconfig_path"
    
    print_success "APP_ROOT updated to: $APP_ROOT"
    print_info "Modified file: $appconfig_path"
    echo ""
    print_info "Content of modified AppConfig.sh:"
    echo "----------------------------------------"
    cat "$appconfig_path"
    echo "----------------------------------------"
    echo ""
    
    # Delete comments from EpgConfig.sh
    if [ -f "$epgconfig_path" ]; then
        print_info "Removing comments from EpgConfig.sh..."
        cp "$epgconfig_path" "${epgconfig_path}.backup.$(date +%Y%m%d_%H%M%S)"
        print_info "Created backup of EpgConfig.sh"
        
        # Remove lines starting with # (comments)
        sed -i '/^[[:space:]]*#/d' "$epgconfig_path"
        
        print_success "Comments removed from EpgConfig.sh"
        print_info "Modified file: $epgconfig_path"
        echo ""
        print_info "Content of modified EpgConfig.sh:"
        echo "----------------------------------------"
        cat "$epgconfig_path"
        echo "----------------------------------------"
        echo ""
    else
        print_warning "EpgConfig.sh not found at: $epgconfig_path"
    fi
}

# ============================================================================
# Step 2: Build (HW or SW)
# ============================================================================
build_project() {
    print_step "STEP 2: Building Project ($BUILD_TYPE)"
    
    cd "$ENV_PATH" || exit 1
    
    print_info "Setting up build environment and running build in tcsh..."
    
    if [ "$BUILD_TYPE" = "HW" ]; then
        print_info "Building Hardware (HW)..."
        print_command "source ME.Develop/BuildSys/TreeConfig.sh && cd ME.Develop/applications/CV && ./wake -m r --rev 6 ht Grab --cvapp GPR_APP"
        tcsh -c "source ME.Develop/BuildSys/TreeConfig.sh && cd ME.Develop/applications/CV && ./wake -m r --rev 6 ht Grab --cvapp GPR_APP"
    elif [ "$BUILD_TYPE" = "SW" ]; then
        print_info "Building Software (SW)..."
        print_command "source ME.Develop/BuildSys/TreeConfig.sh && ./wake -m d --rev 6 st Grab"
        tcsh -c "source ME.Develop/BuildSys/TreeConfig.sh && ./wake -m d --rev 6 st Grab"
    else
        print_error "Invalid BUILD_TYPE: $BUILD_TYPE (must be HW or SW)"
        return 1
    fi
    
    print_success "Build completed successfully"
}

# ============================================================================
# Step 3: Generate Deployment Package
# ============================================================================
generate_package() {
    print_step "STEP 3: Generating Deployment Package"
    
    cd "$ENV_PATH" || exit 1
    
    # Create output directory if it doesn't exist
    local output_dir="$OUTPUT_BASE/$PROJECT_NAME"
    if [ ! -d "$output_dir" ]; then
        print_info "Creating output directory: $output_dir"
        mkdir -p "$output_dir"
    fi
    
    # Get version (you may need to adjust this based on how version is determined)
    local version=$(date +%Y%m%d_%H%M%S)
    local output_path="$output_dir/${PROJECT_NAME}_${version}"
    
    print_info "Output path: $output_path"
    
    print_info "Setting up build environment and running generator in tcsh..."
    print_command "source ME.Develop/BuildSys/TreeConfig.sh && cd ME.Develop/deployment && ./generator.sh -p \"${PROJECT_NAME}_DC\" -o \"$output_path\" -m MOD_IC_EEPROM_DISABLE"
    
    # Run generator in tcsh with environment setup
    tcsh -c "source ME.Develop/BuildSys/TreeConfig.sh && cd ME.Develop/deployment && ./generator.sh -p \"${PROJECT_NAME}_DC\" -o \"$output_path\" -m MOD_IC_EEPROM_DISABLE"
    
    # Check if command succeeded
    if [ $? -ne 0 ]; then
        print_error "Generator command failed"
        return 1
    fi
    
    # Verify output was created
    if [ ! -d "$output_path" ]; then
        print_error "Output directory was not created: $output_path"
        return 1
    fi
    
    # Save the BKC path for deployment
    echo "$output_path/bkc" > "$ENV_PATH/.last_bkc_path"
    
    print_success "Package generated at: $output_path"
}

# ============================================================================
# Step 4: Deploy to Setup
# ============================================================================
deploy_to_setup() {
    print_step "STEP 4: Deploying to Setup"
    
    if [ -z "$SETUP_NAME" ]; then
        print_error "SETUP_NAME not defined in config file"
        return 1
    fi
    
    # Read the BKC path from the last generate step
    local bkc_path
    if [ -f "$ENV_PATH/.last_bkc_path" ]; then
        bkc_path=$(cat "$ENV_PATH/.last_bkc_path")
    else
        print_error "BKC path not found. Please run generate step first."
        return 1
    fi
    
    if [ ! -d "$bkc_path" ]; then
        print_error "BKC directory not found: $bkc_path"
        return 1
    fi
    
    print_info "BKC path: $bkc_path"
    print_info "Connecting to setup: $SETUP_NAME"
    
    # SSH to setup and run deploy
    print_command "ssh $SETUP_NAME"
    ssh "$SETUP_NAME" << EOF
cd "$bkc_path" || exit 1
echo -e "${MAGENTA}[COMMAND]${NC} ./INSTALLER/deploy.py --avpc $AVPC_IP -p $AVPC_PASSWORD"
./INSTALLER/deploy.py --avpc $AVPC_IP -p $AVPC_PASSWORD
EOF
    
    print_success "Deployment completed"
}

# ============================================================================
# Step 5: Install on Setup
# ============================================================================
install_on_setup() {
    print_step "STEP 5: Installing on Setup"
    
    if [ -z "$SETUP_NAME" ]; then
        print_error "SETUP_NAME not defined in config file"
        return 1
    fi
    
    print_info "Connecting to setup: $SETUP_NAME"
    print_info "Installing on AVPC..."
    
    # SSH to setup, then SSH to AVPC and run installer
    print_command "ssh $SETUP_NAME"
    ssh "$SETUP_NAME" << EOF
echo -e "${MAGENTA}[COMMAND]${NC} sshpass -p \"****\" ssh avpc@$AVPC_IP"
sshpass -p "$AVPC_PASSWORD" ssh avpc@$AVPC_IP << 'INNER_EOF'
echo -e "${MAGENTA}[COMMAND]${NC} cd zeroconfig/bkc"
cd zeroconfig/bkc || exit 1
echo -e "${MAGENTA}[COMMAND]${NC} ./installer.sh --burncode -e mcue switch"
./installer.sh --burncode -e mcue switch
INNER_EOF
EOF
    
    print_success "Installation completed"
}

# ============================================================================
# Main Execution
# ============================================================================

print_info "Starting automation script..."
echo ""

# Execute selected steps
if [ "$DO_UPDATE" = true ]; then
    update_app_root || { print_error "Update failed"; exit 1; }
fi

if [ "$DO_BUILD" = true ]; then
    build_project || { print_error "Build failed"; exit 1; }
fi

if [ "$DO_GENERATE" = true ]; then
    generate_package || { print_error "Generate failed"; exit 1; }
fi

if [ "$DO_DEPLOY" = true ]; then
    deploy_to_setup || { print_error "Deploy failed"; exit 1; }
fi

if [ "$DO_INSTALL" = true ]; then
    install_on_setup || { print_error "Install failed"; exit 1; }
fi

print_step "ALL TASKS COMPLETED SUCCESSFULLY!"
print_info "Summary of executed steps:"
[ "$DO_UPDATE" = true ] && echo "  ✓ Updated APP_ROOT"
[ "$DO_BUILD" = true ] && echo "  ✓ Built project ($BUILD_TYPE)"
[ "$DO_GENERATE" = true ] && echo "  ✓ Generated deployment package"
[ "$DO_DEPLOY" = true ] && echo "  ✓ Deployed to setup"
[ "$DO_INSTALL" = true ] && echo "  ✓ Installed on setup"
echo ""
