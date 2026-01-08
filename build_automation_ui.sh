#!/bin/bash

# ============================================================================
# Build Automation UI Script
# ============================================================================
# This script provides an interactive UI for the build automation workflow
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_SCRIPT="$SCRIPT_DIR/build_automation.sh"
DEFAULT_CONFIG="$SCRIPT_DIR/build_config.cfg"

# Current config file
CONFIG_FILE="$DEFAULT_CONFIG"

# Check if dialog or whiptail is available
if command -v dialog &> /dev/null; then
    DIALOG_CMD="dialog"
elif command -v whiptail &> /dev/null; then
    DIALOG_CMD="whiptail"
else
    echo -e "${RED}Error: Neither 'dialog' nor 'whiptail' is installed.${NC}"
    echo "Please install one of them:"
    echo "  Ubuntu/Debian: sudo apt-get install dialog"
    echo "  RHEL/CentOS: sudo yum install dialog"
    exit 1
fi

# Temporary file for dialog output
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Function to show a message box
show_message() {
    local title="$1"
    local message="$2"
    $DIALOG_CMD --title "$title" --msgbox "$message" 10 60
}

# Function to show error message
show_error() {
    $DIALOG_CMD --title "Error" --msgbox "$1" 10 60
}

# Function to show success message
show_success() {
    $DIALOG_CMD --title "Success" --msgbox "$1" 10 60
}

# Function to show yes/no confirmation
confirm_action() {
    local title="$1"
    local message="$2"
    $DIALOG_CMD --title "$title" --yesno "$message" 10 60
    return $?
}

# Function to select config file
select_config_file() {
    local input
    input=$($DIALOG_CMD --title "Select Configuration File" \
        --inputbox "Enter path to configuration file:\n(Leave empty to use default)" \
        12 70 "$CONFIG_FILE" 2>&1 >/dev/tty)
    
    if [ $? -eq 0 ] && [ -n "$input" ]; then
        if [ -f "$input" ]; then
            CONFIG_FILE="$input"
            show_success "Configuration file set to:\n$CONFIG_FILE"
        else
            show_error "File not found: $input"
        fi
    fi
}

# Function to view current configuration
view_config() {
    if [ -f "$CONFIG_FILE" ]; then
        $DIALOG_CMD --title "Current Configuration" \
            --textbox "$CONFIG_FILE" 20 80
    else
        show_error "Configuration file not found: $CONFIG_FILE"
    fi
}

# Function to execute build command
execute_build_command() {
    local options="$1"
    local description="$2"
    
    # Clear screen and show what's being executed
    clear
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Executing: $description${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${BLUE}Config File:${NC} $CONFIG_FILE"
    echo -e "${BLUE}Command:${NC} $BUILD_SCRIPT -c $CONFIG_FILE $options"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Execute the command
    bash "$BUILD_SCRIPT" -c "$CONFIG_FILE" $options
    local exit_code=$?
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}Completed Successfully!${NC}"
    else
        echo -e "${RED}Command Failed (exit code: $exit_code)${NC}"
    fi
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Press Enter to continue..."
    read
    
    return $exit_code
}

# Function to show the main menu
show_main_menu() {
    while true; do
        # Get configuration summary
        local config_summary="Using: $(basename $CONFIG_FILE)"
        if [ -f "$CONFIG_FILE" ]; then
            source "$CONFIG_FILE"
            config_summary="${config_summary}\nProject: ${PROJECT_NAME:-N/A}\nBuild Type: ${BUILD_TYPE:-N/A}"
        fi
        
        local choice
        choice=$($DIALOG_CMD --title "Build Automation UI" \
            --menu "$config_summary\n\nSelect an operation:" 22 70 14 \
            "1" "Update APP_ROOT" \
            "2" "Build Project" \
            "3" "Generate Package" \
            "4" "Deploy to Setup" \
            "5" "Install on Setup" \
            "6" "Build + Generate" \
            "7" "Generate + Deploy" \
            "8" "Deploy + Install" \
            "9" "Update + Build + Generate" \
            "0" "Execute All Steps" \
            "---" "---" \
            "C" "Select Config File" \
            "V" "View Current Config" \
            "Q" "Quit" \
            2>&1 >/dev/tty)
        
        local status=$?
        
        # Check if user canceled
        if [ $status -ne 0 ]; then
            break
        fi
        
        case $choice in
            1)
                if confirm_action "Confirm Update" "Update APP_ROOT in AppConfig.sh?"; then
                    execute_build_command "-u" "Update APP_ROOT"
                fi
                ;;
            2)
                if confirm_action "Confirm Build" "Build the project?\n\nThis may take a while depending on the build type."; then
                    execute_build_command "-b" "Build Project"
                fi
                ;;
            3)
                if confirm_action "Confirm Generate" "Generate deployment package?"; then
                    execute_build_command "-g" "Generate Package"
                fi
                ;;
            4)
                if confirm_action "Confirm Deploy" "Deploy to setup?"; then
                    execute_build_command "-d" "Deploy to Setup"
                fi
                ;;
            5)
                if confirm_action "Confirm Install" "Install on setup?"; then
                    execute_build_command "-i" "Install on Setup"
                fi
                ;;
            6)
                if confirm_action "Confirm Build + Generate" "Build project and generate package?"; then
                    execute_build_command "-b -g" "Build + Generate"
                fi
                ;;
            7)
                if confirm_action "Confirm Generate + Deploy" "Generate package and deploy to setup?"; then
                    execute_build_command "-g -d" "Generate + Deploy"
                fi
                ;;
            8)
                if confirm_action "Confirm Deploy + Install" "Deploy to setup and install?"; then
                    execute_build_command "-d -i" "Deploy + Install"
                fi
                ;;
            9)
                if confirm_action "Confirm Update + Build + Generate" "Update, build, and generate package?"; then
                    execute_build_command "-u -b -g" "Update + Build + Generate"
                fi
                ;;
            0)
                if confirm_action "Confirm Execute All" "Execute ALL steps?\n\n- Update APP_ROOT\n- Build Project\n- Generate Package\n- Deploy to Setup\n- Install on Setup\n\nThis will take a long time!"; then
                    execute_build_command "-a" "Execute All Steps"
                fi
                ;;
            C)
                select_config_file
                ;;
            V)
                view_config
                ;;
            Q)
                break
                ;;
            ---)
                # Separator, do nothing
                ;;
        esac
    done
}

# Function to show welcome screen
show_welcome() {
    $DIALOG_CMD --title "Build Automation UI" \
        --msgbox "Welcome to Build Automation UI\n\nThis interface provides easy access to:\n\n• Update APP_ROOT\n• Build (Compile) Project\n• Generate Deployment Package\n• Deploy to Setup\n• Install on Setup\n\nYou can execute steps individually or in combination.\n\nPress OK to continue..." 18 60
}

# ============================================================================
# Main Execution
# ============================================================================

# Check if build script exists
if [ ! -f "$BUILD_SCRIPT" ]; then
    echo -e "${RED}Error: Build automation script not found at:${NC}"
    echo "$BUILD_SCRIPT"
    exit 1
fi

# Check if default config exists
if [ ! -f "$DEFAULT_CONFIG" ]; then
    echo -e "${YELLOW}Warning: Default config file not found at:${NC}"
    echo "$DEFAULT_CONFIG"
fi

# Show welcome screen
show_welcome

# Show main menu
show_main_menu

# Cleanup and exit
clear
echo -e "${GREEN}Thank you for using Build Automation UI!${NC}"
echo ""
