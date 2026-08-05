#!/bin/bash

echo "==================================================="
echo "  ARIA - AI Research Assistant Setup"
echo "==================================================="
echo ""

if [ ! -f ".env" ]; then
    echo "[INFO] Creating .env file from .env.example..."
    cp .env.example .env
fi

echo "Please enter the full path to your Obsidian vault where ARIA should operate."
echo "Example: /Users/YourName/Documents/ObsidianVault"
read -p "Vault Path: " VAULT_PATH

if [ -z "$VAULT_PATH" ]; then
    echo "[ERROR] Vault path cannot be empty."
    exit 1
fi

echo ""
echo "[INFO] Updating .env with your vault path..."

# Replace the vault path in .env (compatible with macOS and Linux sed)
sed -i.bak "s|^OBSIDIAN_VAULT_PATH=.*|OBSIDIAN_VAULT_PATH=$VAULT_PATH|g" .env
rm -f .env.bak

echo "[INFO] Starting ARIA using Docker..."
docker-compose up -d --build

echo ""
echo "==================================================="
echo "  Setup Complete!"
echo "  ARIA is now running in the background."
echo "  Check your Obsidian vault for the new ARIA folders."
echo "==================================================="
