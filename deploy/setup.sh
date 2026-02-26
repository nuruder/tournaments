#!/bin/bash
set -e

APP_DIR="/opt/tournament_bot"
REPO="https://github.com/nuruder/tournaments.git"

# Create bot user (if not exists)
if ! id "bot" &>/dev/null; then
    sudo useradd -m -s /bin/bash bot
    echo "Created user 'bot'"
fi

# Create app dir and clone repo
if [ ! -d "$APP_DIR/.git" ]; then
    sudo mkdir -p "$APP_DIR"
    sudo chown bot:bot "$APP_DIR"
    sudo -u bot git clone "$REPO" "$APP_DIR"
else
    echo "Repo already exists, pulling latest..."
    cd "$APP_DIR" && sudo -u bot git pull
fi

cd "$APP_DIR"

# Create venv and install deps
sudo -u bot python3 -m venv venv
sudo -u bot venv/bin/pip install -r requirements.txt

# Create .env if not exists
if [ ! -f .env ]; then
    sudo -u bot cp .env.example .env
    echo ""
    echo "========================================="
    echo " EDIT .env FILE WITH YOUR CREDENTIALS:"
    echo " nano $APP_DIR/.env"
    echo "========================================="
    echo ""
fi

# Install systemd service
sudo cp deploy/tournaments-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tournaments-bot

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env:    sudo -u bot nano $APP_DIR/.env"
echo "  2. Edit venues:  sudo -u bot nano $APP_DIR/venues.txt"
echo "  3. Start bot:    sudo systemctl start tournaments-bot"
echo "  4. Check logs:   sudo journalctl -u tournaments-bot -f"
