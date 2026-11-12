#!/bin/bash
echo "Git workflow starting..."

# Add all changes
git add .

# Commit with timestamp
git commit -m "Update: $(date)"

# Push to GitHub
git push origin main

echo "Changes pushed to GitHub successfully!"