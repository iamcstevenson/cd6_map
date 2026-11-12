#!/bin/bash
echo "Starting deployment process..."

# Activate virtual environment
source ~/Development/mapping_project_env/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run the application
python src/app.py &

echo "Deployment complete!"