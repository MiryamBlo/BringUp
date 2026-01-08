# Build Automation Project

This project contains scripts to automate the build, generate, deploy, and install workflow for Mobileye projects.

## Files

- `build_automation.sh` - Main automation script
- `build_config.cfg` - Configuration file with project settings

## Setup

1. Edit `build_config.cfg` with your project settings:
   - `APP_ROOT` - Application root path
   - `PROJECT_NAME` - Your project name
   - `SETUP_NAME` - SSH hostname for deployment
   - `ENV_PATH` - Base path for the workspace
   - `BUILD_TYPE` - HW or SW
   - Other settings as needed

2. Make the script executable:
   ```bash
   chmod +x build_automation.sh
   ```

## Usage

```bash
./build_automation.sh -c build_config.cfg [OPTIONS]
```

### Options

- `-c <config_file>` - Path to configuration file (required)
- `-u` - Update APP_ROOT in AppConfig.sh
- `-b` - Build (compile HW or SW based on config)
- `-g` - Generate deployment package
- `-d` - Deploy to setup
- `-i` - Install on setup
- `-a` - Execute all steps
- `-h` - Show help message

### Examples

```bash
# Update APP_ROOT and build only
./build_automation.sh -c build_config.cfg -u -b

# Generate and deploy
./build_automation.sh -c build_config.cfg -g -d

# Execute all steps
./build_automation.sh -c build_config.cfg -a
```

## Workflow Steps

1. **Update APP_ROOT** - Updates the APP_ROOT value in `ME.Develop/BuildSys/AppConfig.sh`
2. **Build** - Compiles HW or SW based on configuration
3. **Generate** - Creates deployment package using generator.sh
4. **Deploy** - Deploys to the target setup via SSH
5. **Install** - Installs the package on the AVPC

## Notes

- The script sources `TreeConfig.sh` before build and generate steps
- Backups are created before modifying AppConfig.sh
- The BKC path is automatically tracked between generate and deploy steps
