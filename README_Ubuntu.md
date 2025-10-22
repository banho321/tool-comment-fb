# Facebook Bot - Ubuntu Setup Guide

## 🚀 Quick Start

### 1. Setup Ubuntu Server
```bash
# Clone repository
git clone <your-repo-url>
cd tool-fb

# Run setup script
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

### 2. Login to Facebook
```bash
# Activate virtual environment
source venv/bin/activate

# Login to Facebook (this will open browser)
python -m src.login_helper --account acc1
```

### 3. Start Bot

#### Option A: Manual Start
```bash
# Start bot manually
./start_bot.sh
```

#### Option B: Systemd Service (Recommended)
```bash
# Start as system service
sudo systemctl start facebook-bot

# Check status
sudo systemctl status facebook-bot

# View logs
sudo journalctl -u facebook-bot -f
```

#### Option C: Docker
```bash
# Build Docker image
docker build -t facebook-bot .

# Run container
docker run -d --name facebook-bot \
  -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/data:/app/data \
  facebook-bot
```

## 🔧 Configuration

### Bot Settings
Edit `config.yaml`:
```yaml
settings:
  headless_browser: true  # Set to false for debugging
  max_posts_to_scan_per_group: 20
  max_post_age_days: 3
  dry_run: false  # Set to true for testing
```

### Continuous Runner Settings
```bash
# Run every 30 minutes (default)
python continuous_runner.py --account acc1 --interval 30

# Run once and exit
python continuous_runner.py --account acc1 --once

# Run every 60 minutes
python continuous_runner.py --account acc1 --interval 60
```

## 📊 Monitoring

### Check Bot Status
```bash
# Check if bot is running
ps aux | grep continuous_runner

# Check systemd service
sudo systemctl status facebook-bot

# View logs
tail -f continuous_runner.log
```

### Monitor and Auto-restart
```bash
# Start monitor (auto-restart if bot crashes)
python monitor_bot.py --account acc1 --interval 60
```

## 🛠️ Troubleshooting

### Common Issues

1. **Session expired**
   ```bash
   # Re-login
   python -m src.login_helper --account acc1
   ```

2. **Firefox not found**
   ```bash
   # Install Firefox
   sudo apt install firefox
   ```

3. **Permission denied**
   ```bash
   # Fix permissions
   chmod +x *.py *.sh
   ```

4. **Bot not starting**
   ```bash
   # Check logs
   tail -f continuous_runner.log
   
   # Check systemd logs
   sudo journalctl -u facebook-bot -f
   ```

### Log Files
- `continuous_runner.log` - Main bot logs
- `monitor.log` - Monitor logs
- `bot.log` - Application logs

## 🔄 Maintenance

### Update Bot
```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart facebook-bot
```

### Backup Data
```bash
# Backup sessions and data
tar -czf backup_$(date +%Y%m%d).tar.gz sessions/ data/
```

### Stop Bot
```bash
# Stop systemd service
sudo systemctl stop facebook-bot

# Stop manual process
pkill -f continuous_runner

# Stop Docker container
docker stop facebook-bot
```

## 📈 Performance Tips

1. **Use headless mode** for better performance
2. **Adjust interval** based on your needs (30-60 minutes)
3. **Monitor logs** regularly
4. **Backup sessions** periodically
5. **Use SSD storage** for better performance

## 🔒 Security

1. **Don't run as root**
2. **Use firewall** to restrict access
3. **Regular updates**
4. **Monitor logs** for suspicious activity
5. **Backup sessions** securely
