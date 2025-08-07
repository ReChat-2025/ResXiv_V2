"""
Email Service

Handles sending emails for user authentication, notifications, and other purposes.
Uses SMTP with Gmail or other email providers.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
from datetime import datetime

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailUrlConfig:
    """
    Centralized URL configuration for email links following SOLID principles.
    Single Responsibility: Manages all email-related URL generation.
    """
    
    def __init__(self):
        self.base_url = self._get_base_url()
        self.use_https = self._should_use_https()
    
    def _get_base_url(self) -> str:
        """Get base URL from settings or environment"""
        # Check if frontend_url is configured in settings
        if hasattr(settings, 'frontend_url') and settings.frontend_url:
            return settings.frontend_url.rstrip('/')
        
        # Fallback to domain-based URL
        domain = getattr(settings, 'domain', 'cbeta.resxiv.com')
        protocol = 'https' if self._should_use_https() else 'http'
        return f"{protocol}://{domain}"
    
    def _should_use_https(self) -> bool:
        """Determine if HTTPS should be used based on environment"""
        # Use HTTPS for production domains
        base_url = getattr(settings, 'frontend_url', '') or getattr(settings, 'domain', '')
        return not ('localhost' in base_url or '127.0.0.1' in base_url)
    
    def get_verification_url(self, token: str) -> str:
        """Generate email verification URL"""
        return f"{self.base_url}/verify-email?token={token}"
    
    def get_password_reset_url(self, token: str) -> str:
        """Generate password reset URL"""
        return f"{self.base_url}/reset-password?token={token}"
    
    def get_project_invitation_url(self, token: str) -> str:
        """Generate project invitation URL"""
        return f"{self.base_url}/projects/invite?token={token}"
    
    def get_dashboard_url(self) -> str:
        """Get dashboard URL"""
        return f"{self.base_url}/projects"


class EmailService:
    """Service for sending emails via SMTP"""
    
    def __init__(self):
        self.smtp_host = settings.email.smtp_host
        self.smtp_port = settings.email.smtp_port
        self.smtp_username = settings.email.smtp_username
        self.smtp_password = settings.email.smtp_password
        self.smtp_tls = settings.email.smtp_tls
        self.from_email = settings.email.from_email or self.smtp_username
        
        # Initialize URL configuration
        self.url_config = EmailUrlConfig()

        # If using Gmail SMTP but from_email domain differs, fall back to smtp_username
        if self.smtp_host.endswith("gmail.com") and self.smtp_username and self.from_email.split("@")[-1] != "gmail.com":
            logger.warning("FROM_EMAIL domain differs from Gmail SMTP username; using smtp_username as sender to satisfy Gmail policy")
            self.from_email = self.smtp_username
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Send email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            attachments: List of file paths to attach (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email
            
            # Add plain text part
            text_part = MIMEText(body, "plain")
            message.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                message.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    await self._add_attachment(message, file_path)
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls(context=context)
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.sendmail(self.from_email, to_email, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def _add_attachment(self, message: MIMEMultipart, file_path: str):
        """Add file attachment to email message"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.warning(f"Attachment file not found: {file_path}")
                return
            
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {file_path.name}",
            )
            
            message.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {str(e)}")
    
    async def send_email_verification(
        self,
        to_email: str,
        name: str,
        verification_token: str
    ) -> bool:
        """
        Send email verification email
        
        Args:
            to_email: User's email address
            name: User's name
            verification_token: Verification token
            
        Returns:
            True if email sent successfully
        """
        verification_url = self.url_config.get_verification_url(verification_token)
        
        subject = f"Welcome to {settings.app_name} - Verify Your Email"
        
        # Plain text version
        body = f"""
Hi {name},

Welcome to {settings.app_name}! 

To complete your registration, please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account with us, please ignore this email.

Best regards,
The {settings.app_name} Team
        """.strip()
        
        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Verify Your Email - {settings.app_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #007bff; 
            color: white; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 20px 0;
        }}
        .footer {{ 
            background-color: #f8f9fa; 
            padding: 20px; 
            text-align: center; 
            font-size: 12px; 
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{settings.app_name}</h1>
        </div>
        <div class="content">
            <h2>Welcome, {name}!</h2>
            <p>Thank you for joining {settings.app_name}, the unified research collaboration platform.</p>
            <p>To complete your registration and start collaborating with researchers worldwide, please verify your email address:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                {verification_url}
            </p>
            <p><strong>This link will expire in 24 hours.</strong></p>
            <p>If you didn't create an account with us, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>This email was sent by {settings.app_name}. If you have any questions, please contact our support team.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return await self.send_email(to_email, subject, body, html_body)
    
    async def send_password_reset(
        self,
        to_email: str,
        name: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email
        
        Args:
            to_email: User's email address
            name: User's name
            reset_token: Password reset token
            
        Returns:
            True if email sent successfully
        """
        reset_url = self.url_config.get_password_reset_url(reset_token)
        
        subject = f"Reset Your {settings.app_name} Password"
        
        # Plain text version
        body = f"""
Hi {name},

We received a request to reset your password for your {settings.app_name} account.

To reset your password, click the link below:

{reset_url}

This link will expire in 2 hours for security reasons.

If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

Best regards,
The {settings.app_name} Team
        """.strip()
        
        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reset Your Password - {settings.app_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #dc3545; 
            color: white; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 20px 0;
        }}
        .footer {{ 
            background-color: #f8f9fa; 
            padding: 20px; 
            text-align: center; 
            font-size: 12px; 
            color: #666;
        }}
        .warning {{ 
            background-color: #fff3cd; 
            border: 1px solid #ffeaa7; 
            padding: 10px; 
            border-radius: 4px; 
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{settings.app_name}</h1>
        </div>
        <div class="content">
            <h2>Password Reset Request</h2>
            <p>Hi {name},</p>
            <p>We received a request to reset your password for your {settings.app_name} account.</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
                {reset_url}
            </p>
            <div class="warning">
                <strong>Security Notice:</strong> This link will expire in 2 hours for your security.
            </div>
            <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
        </div>
        <div class="footer">
            <p>For security reasons, never share this email with anyone.</p>
            <p>This email was sent by {settings.app_name}.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return await self.send_email(to_email, subject, body, html_body)
    
    async def send_welcome_email(
        self,
        to_email: str,
        name: str
    ) -> bool:
        """
        Send welcome email after email verification
        
        Args:
            to_email: User's email address
            name: User's name
            
        Returns:
            True if email sent successfully
        """
        subject = f"Welcome to {settings.app_name} - Let's Get Started!"
        
        # Plain text version
        body = f"""
Hi {name},

Welcome to {settings.app_name}! Your email has been verified and your account is now active.

Here's what you can do next:

1. Complete your profile: Add your research interests and a brief introduction
2. Create your first project: Start collaborating with other researchers
3. Upload papers: Add research papers to your projects for discussion and analysis
4. Invite collaborators: Bring your team members to the platform

Visit your dashboard: {self.url_config.get_dashboard_url()}

If you have any questions or need help getting started, don't hesitate to reach out to our support team.

Happy researching!

Best regards,
The {settings.app_name} Team
        """.strip()
        
        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome to {settings.app_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .button {{ 
            display: inline-block; 
            padding: 12px 24px; 
            background-color: #28a745; 
            color: white; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 20px 0;
        }}
        .steps {{ background-color: #f8f9fa; padding: 20px; border-radius: 4px; margin: 20px 0; }}
        .step {{ margin: 10px 0; }}
        .footer {{ 
            background-color: #f8f9fa; 
            padding: 20px; 
            text-align: center; 
            font-size: 12px; 
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to {settings.app_name}!</h1>
        </div>
        <div class="content">
            <p>Hi {name},</p>
            <p>Congratulations! Your email has been verified and your account is now active. You're all set to start your research collaboration journey.</p>
            
            <div class="steps">
                <h3>What's next? Here are some great first steps:</h3>
                <div class="step">📝 <strong>Complete your profile:</strong> Add your research interests and introduction</div>
                <div class="step">🚀 <strong>Create your first project:</strong> Start collaborating with other researchers</div>
                <div class="step">📄 <strong>Upload papers:</strong> Add research papers for discussion and analysis</div>
                <div class="step">👥 <strong>Invite collaborators:</strong> Bring your team members to the platform</div>
            </div>
            
            <p style="text-align: center;">
                <a href="{self.url_config.get_dashboard_url()}" class="button">Go to Dashboard</a>
            </p>
            
            <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
            <p>Happy researching! 🔬</p>
        </div>
        <div class="footer">
            <p>This email was sent by {settings.app_name}. We're excited to have you on board!</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return await self.send_email(to_email, subject, body, html_body)
    
    async def send_test_email(self, to_email: str) -> bool:
        """Send a test email to verify SMTP configuration"""
        subject = f"Test Email from {settings.app_name}"
        body = f"""
This is a test email from {settings.app_name}.

If you received this email, your SMTP configuration is working correctly!

Timestamp: {datetime.now().isoformat()}
        """.strip()
        
        return await self.send_email(to_email, subject, body)

    async def send_project_invitation(
        self,
        to_email: str,
        inviter_name: str,
        project_name: str,
        invitation_token: str,
    ) -> bool:
        """Send a project invitation e-mail with an accept link."""
        accept_url = self.url_config.get_project_invitation_url(invitation_token)
        subject = f"You\'ve been invited to join '{project_name}' on {settings.app_name}"
        body = (
            f"Hi,\n\n"
            f"{inviter_name} has invited you to collaborate on the project '{project_name}'.\n"
            f"Click the link below to accept the invitation:\n{accept_url}\n\n"
            f"If you weren\'t expecting this e-mail, you can safely ignore it."
        )
        html_body = (
            f"<p>Hi,</p>"
            f"<p><strong>{inviter_name}</strong> has invited you to collaborate on the project <strong>{project_name}</strong>.</p>"
            f"<p><a href=\"{accept_url}\">Accept the invitation</a></p>"
            f"<p>If you weren\'t expecting this e-mail, you can safely ignore it.</p>"
        )
        return await self.send_email(to_email, subject, body, html_body)


# Utility function to get email service instance
def get_email_service() -> EmailService:
    """Get email service instance"""
    return EmailService() 