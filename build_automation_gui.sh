#!/bin/bash

# ============================================================================
# Build Automation GUI Script
# ============================================================================
# This script provides a graphical user interface with buttons for the 
# build automation workflow
# ============================================================================

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_SCRIPT="$SCRIPT_DIR/build_automation.sh"
DEFAULT_CONFIG="$SCRIPT_DIR/build_config.cfg"

# Current config file
CONFIG_FILE="$DEFAULT_CONFIG"

# Check if zenity is available
if ! command -v zenity &> /dev/null; then
    echo "Error: 'zenity' is not installed."
    echo "Please install it:"
    echo "  Ubuntu/Debian: sudo apt-get install zenity"
    echo "  RHEL/CentOS: sudo yum install zenity"
    exit 1
fi

# Function to show info dialog
show_info() {
    zenity --info --title="Build Automation" --text="$1" --width=400 --height=200
}

# Function to show error dialog
show_error() {
    zenity --error --title="Build Automation - Error" --text="$1" --width=400 --height=200
}

# Function to show warning dialog
show_warning() {
    zenity --warning --title="Build Automation - Warning" --text="$1" --width=400 --height=200
}

# Function to ask yes/no question
ask_confirmation() {
    zenity --question --title="Confirm Action" --text="$1" --width=400 --height=150
    return $?
}

# Function to select config file
select_config_file() {
    local new_config
    new_config=$(zenity --file-selection --title="Select Configuration File" --filename="$CONFIG_FILE" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$new_config" ]; then
        if [ -f "$new_config" ]; then
            CONFIG_FILE="$new_config"
            show_info "Configuration file set to:\n\n$CONFIG_FILE"
        else
            show_error "File not found: $new_config"
        fi
    fi
}

# Function to view current configuration
view_config() {
    if [ -f "$CONFIG_FILE" ]; then
        zenity --text-info --title="Current Configuration" --filename="$CONFIG_FILE" --width=600 --height=400
    else
        show_error "Configuration file not found:\n$CONFIG_FILE"
    fi
}

# Function to execute build command
execute_build_command() {
    local options="$1"
    local description="$2"
    
    # Show progress dialog
    (
        echo "# Executing: $description"
        echo "# Config: $(basename $CONFIG_FILE)"
        echo "# Command: build_automation.sh -c $CONFIG_FILE $options"
        echo "10"
        sleep 1
        
        # Execute the command in background and capture output
        bash "$BUILD_SCRIPT" -c "$CONFIG_FILE" $options > /tmp/build_output_$$.log 2>&1
        local exit_code=$?
        
        echo "100"
        
        # Show result
        if [ $exit_code -eq 0 ]; then
            zenity --info --title="Success" --text="$description completed successfully!\n\nSee details in terminal or log." --width=400 --height=200
        else
            zenity --error --title="Failed" --text="$description failed!\n\nExit code: $exit_code\n\nCheck /tmp/build_output_$$.log for details" --width=400 --height=200
        fi
        
        # Offer to view log
        if zenity --question --title="View Log" --text="Would you like to view the execution log?" --width=350 --height=100; then
            zenity --text-info --title="Execution Log" --filename=/tmp/build_output_$$.log --width=800 --height=600
        fi
        
        rm -f /tmp/build_output_$$.log
        
    ) | zenity --progress --title="Executing..." --text="Initializing..." --percentage=0 --auto-close --width=400
}

# Function to get config summary
get_config_summary() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE" 2>/dev/null
        echo "<b>Current Configuration:</b>
Config File: $(basename $CONFIG_FILE)
Project: ${PROJECT_NAME:-N/A}
Build Type: ${BUILD_TYPE:-N/A}
Environment: ${ENV_PATH:-N/A}"
    else
        echo "<b>Current Configuration:</b>
Config File: $(basename $CONFIG_FILE)
Status: <span color='red'>Not Found</span>"
    fi
}

# Function to show main window with buttons
show_main_window() {
    while true; do
        # Get configuration summary
        local config_info=$(get_config_summary)
        
        # Show main selection dialog with list
        local choice
        choice=$(zenity --list \
            --title="Build Automation - Main Menu" \
            --text="$config_info\n\n<b>Select an operation:</b>" \
            --column="Action" --column="Description" \
            --width=700 --height=600 \
            --hide-column=1 \
            "UPDATE" "Update APP_ROOT" \
            "BUILD" "Build Project (Compile)" \
            "GENERATE" "Generate Deployment Package" \
            "DEPLOY" "Deploy to Setup" \
            "INSTALL" "Install on Setup" \
            "SEP1" "─────────────────────────────────────" \
            "BUILD_GEN" "Build + Generate" \
            "GEN_DEPLOY" "Generate + Deploy" \
            "DEPLOY_INST" "Deploy + Install" \
            "UPDATE_BUILD_GEN" "Update + Build + Generate" \
            "ALL" "Execute All Steps" \
            "SEP2" "─────────────────────────────────────" \
            "CONFIG" "Select Config File" \
            "VIEW" "View Current Config" \
            "QUIT" "Quit" \
            2>/dev/null)
        
        local status=$?
        
        # Check if user canceled
        if [ $status -ne 0 ]; then
            if ask_confirmation "Are you sure you want to exit?"; then
                break
            else
                continue
            fi
        fi
        
        case $choice in
            UPDATE)
                if ask_confirmation "Update APP_ROOT in AppConfig.sh?"; then
                    execute_build_command "-u" "Update APP_ROOT"
                fi
                ;;
            BUILD)
                if ask_confirmation "Build the project?\n\nThis may take a while depending on the build type."; then
                    execute_build_command "-b" "Build Project"
                fi
                ;;
            GENERATE)
                if ask_confirmation "Generate deployment package?"; then
                    execute_build_command "-g" "Generate Package"
                fi
                ;;
            DEPLOY)
                if ask_confirmation "Deploy to setup?"; then
                    execute_build_command "-d" "Deploy to Setup"
                fi
                ;;
            INSTALL)
                if ask_confirmation "Install on setup?"; then
                    execute_build_command "-i" "Install on Setup"
                fi
                ;;
            BUILD_GEN)
                if ask_confirmation "Build project and generate package?"; then
                    execute_build_command "-b -g" "Build + Generate"
                fi
                ;;
            GEN_DEPLOY)
                if ask_confirmation "Generate package and deploy to setup?"; then
                    execute_build_command "-g -d" "Generate + Deploy"
                fi
                ;;
            DEPLOY_INST)
                if ask_confirmation "Deploy to setup and install?"; then
                    execute_build_command "-d -i" "Deploy + Install"
                fi
                ;;
            UPDATE_BUILD_GEN)
                if ask_confirmation "Update, build, and generate package?"; then
                    execute_build_command "-u -b -g" "Update + Build + Generate"
                fi
                ;;
            ALL)
                if ask_confirmation "Execute ALL steps?\n\n• Update APP_ROOT\n• Build Project\n• Generate Package\n• Deploy to Setup\n• Install on Setup\n\nThis will take a long time!"; then
                    execute_build_command "-a" "Execute All Steps"
                fi
                ;;
            CONFIG)
                select_config_file
                ;;
            VIEW)
                view_config
                ;;
            QUIT)
                if ask_confirmation "Are you sure you want to exit?"; then
                    break
                fi
                ;;
            SEP1|SEP2)
                # Separator, do nothing
                ;;
            *)
                if [ -z "$choice" ]; then
                    if ask_confirmation "Are you sure you want to exit?"; then
                        break
                    fi
                fi
                ;;
        esac
    done
}

# ============================================================================
# Main Execution
# ============================================================================

# Check if build script exists
if [ ! -f "$BUILD_SCRIPT" ]; then
    show_error "Build automation script not found at:\n\n$BUILD_SCRIPT"
    exit 1
fi

# Check if default config exists
if [ ! -f "$DEFAULT_CONFIG" ]; then
    show_warning "Default config file not found at:\n\n$DEFAULT_CONFIG"
fi

# Show welcome message
zenity --info \
    --title="Build Automation GUI" \
    --text="<big><b>Welcome to Build Automation GUI</b></big>\n\nThis interface provides easy access to:\n\n• <b>Update</b> APP_ROOT\n• <b>Build</b> (Compile) Project\n• <b>Generate</b> Deployment Package\n• <b>Deploy</b> to Setup\n• <b>Install</b> on Setup\n\nYou can execute steps individually or in combination.\n\nClick OK to continue..." \
    --width=500 --height=300

# Show main window
show_main_window

# Exit message
zenity --info \
    --title="Goodbye" \
    --text="Thank you for using Build Automation GUI!" \
    --width=350 --height=150 \
    --timeout=3

exit 0
