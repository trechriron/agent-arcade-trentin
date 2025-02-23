#!/bin/bash
set -e

echo "🎮 Creating and Activating virtual environment..."

# Function to handle errors
handle_error() {
    echo "❌ Error occurred in install.sh:"
    echo "  Line: $1"
    echo "  Exit code: $2"
    echo "Please check the error message above and try again."
    exit 1
}

# Set up error handling
trap 'handle_error ${LINENO} $?' ERR

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check Python version is >= 3.9 and < 3.13
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [ "$(printf '%s\n' "3.9" "$python_version" | sort -V | head -n1)" != "3.9" ] || [ "$(printf '%s\n' "3.13" "$python_version" | sort -V | head -n1)" != "$python_version" ]; then
    echo "❌ Python version must be between 3.9 and 3.12. Found version: $python_version"
    exit 1
fi

# Check disk space before starting
echo "🔍 Checking system requirements..."
required_space=2048  # 2GB in MB
available_space=$(df -m . | awk 'NR==2 {print $4}')
if [ "$available_space" -lt "$required_space" ]; then
    echo "❌ Insufficient disk space. Required: 2GB, Available: $((available_space/1024))GB"
    exit 1
fi

# Check memory
total_memory=$(sysctl -n hw.memsize 2>/dev/null || free -b | awk '/^Mem:/{print $2}')
total_memory_gb=$((total_memory/1024/1024/1024))
if [ "$total_memory_gb" -lt 4 ]; then
    echo "⚠️  Warning: Less than 4GB RAM detected. Training performance may be impacted."
fi

# for easy copy/pasta
# rm -rf drl-env

# Check if virtual environment exists
if [ ! -d "drl-env" ]; then
    echo "🔧 Creating virtual environment..."
    python3.11 -m venv drl-env
fi

echo "Now run the following command to activate the virtual environment:"
echo "source drl-env/bin/activate"
echo "then run: chmod +x install_in_venv.sh && ./install_in_venv.sh"