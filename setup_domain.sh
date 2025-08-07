#!/bin/bash

# ResXiv V2 - Domain Setup Script
echo "🚀 Setting up ResXiv V2 with your domain..."

# Get domain from user
read -p "Enter your domain name (e.g., resxiv.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "❌ Domain is required!"
    exit 1
fi

echo "✅ Using domain: $DOMAIN"

# Update nginx configuration
echo "🔧 Configuring nginx..."
sed -i "s/your-domain.com/$DOMAIN/g" nginx.conf

# Install certbot if not exists
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot for SSL..."
    sudo yum install -y certbot python3-certbot-nginx
fi

# Copy nginx config
echo "📝 Installing nginx configuration..."
sudo cp nginx.conf /etc/nginx/conf.d/resxiv.conf

# Test nginx config
sudo nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration error!"
    exit 1
fi

# Reload nginx
sudo systemctl reload nginx
sudo systemctl enable nginx

echo "🔒 Setting up SSL certificate..."
echo "Run this command to get SSL certificate:"
echo "sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Point your domain DNS A record to: 35.154.171.72"
echo "2. Run: sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo "3. Start your services:"
echo "   - Frontend: cd frontend && npm run dev -- --hostname 0.0.0.0"
echo "   - Backend: cd backend/resxiv_backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Your app will be available at: https://$DOMAIN" 