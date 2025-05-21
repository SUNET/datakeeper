#!/bin/bash

# Script to convert .env file variables to permanent environment variables
# Usage: ./env_to_permanent.sh [.env_file_path]

set -e  # Exit immediately if a command exits with a non-zero status

# Function to detect shell configuration file
detect_shell_config() {
    local shell_name=$(basename "$SHELL")
    
    case "$shell_name" in
        bash)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS uses .bash_profile by convention
                if [ -f "$HOME/.bash_profile" ]; then
                    echo "$HOME/.bash_profile"
                else
                    echo "$HOME/.bashrc"
                fi
            else
                echo "$HOME/.bashrc"
            fi
            ;;
        zsh)
            echo "$HOME/.zshrc"
            ;;
        fish)
            echo "$HOME/.config/fish/config.fish"
            ;;
        *)
            echo "$HOME/.profile"  # Default fallback
            ;;
    esac
}

# Function to add variables to shell config file
add_to_shell_config() {
    local config_file="$1"
    local env_file="$2"
    local shell_name=$(basename "$SHELL")
    
    echo -e "\n# Environment variables imported from $env_file on $(date)" >> "$config_file"
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Remove inline comments and leading/trailing whitespace
        line=$(echo "$line" | sed 's/#.*$//' | xargs)
        
        # Skip if line is empty after processing
        if [[ -z "$line" ]]; then
            continue
        fi
        
        # Parse variable name and value
        if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
            local var_name="${BASH_REMATCH[1]}"
            local var_value="${BASH_REMATCH[2]}"
            
            # Remove quotes if present
            var_value=$(echo "$var_value" | sed -E 's/^"(.*)"$/\1/' | sed -E "s/^'(.*)'$/\1/")
            
            # Handle different shell syntaxes
            case "$shell_name" in
                fish)
                    echo "set -gx $var_name \"$var_value\"" >> "$config_file"
                    ;;
                *)
                    echo "export $var_name=\"$var_value\"" >> "$config_file"
                    ;;
            esac
            
            echo "Added $var_name to $config_file"
        fi
    done < "$env_file"
    
    echo -e "\nEnvironment variables have been added to $config_file"
    echo "To apply them immediately, run:"
    
    case "$shell_name" in
        fish)
            echo "source $config_file"
            ;;
        *)
            echo "source $config_file"
            ;;
    esac
}

# Main script execution
main() {
    # Get .env file path from argument or use default
    local env_file="${1:-.env}"
    
    # Check if .env file exists
    if [ ! -f "$env_file" ]; then
        echo "Error: $env_file file not found!"
        echo "Usage: $0 [.env_file_path]"
        exit 1
    fi
    
    # Detect shell configuration file
    local config_file=$(detect_shell_config)
    
    # Create backup of shell config file
    if [ -f "$config_file" ]; then
        cp "$config_file" "${config_file}.backup.$(date +%Y%m%d%H%M%S)"
        echo "Created backup of $config_file"
    fi
    
    # Add environment variables to shell config
    add_to_shell_config "$config_file" "$env_file"
    
    echo -e "\nDone! Your environment variables from $env_file have been permanently added to $config_file"
    echo "Close and reopen your terminal or run 'source $config_file' to apply the changes."
}

# Execute main function
main "$@"

# chmod +x env_to_permanent.sh
# ./env_to_permanent.sh /path/to/your/.env
