import os
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()


def init_mail(app):
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1")
    app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1")
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
        "MAIL_DEFAULT_SENDER",
        os.getenv("MAIL_USERNAME")
    )

    mail.init_app(app)


def send_resolution_email(problem):
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")

    if not username or not password or "yourgmail" in username or "change_this" in password:
        raise RuntimeError("Email service credentials not properly configured in .env.")

    msg = Message(
        subject=f"🌊 FloodGuard AI - Incident #FG{problem['id']} Resolved",
        recipients=[problem["email"]],
        body=f"""
Dear {problem['name']},

Good news! Your reported flood problem has been marked as COMPLETED by our emergency response team.

Complaint ID: FG{problem['id']}
Problem: {problem['title']}
Reported Location: {problem['location']}

Agent Resolution Remarks:
{problem['remarks']}

Thank you for helping us keep the community safe.

Regards,
FloodGuard AI Emergency Response Team
"""
    )

    msg.html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 10px; background-color: #f8fafc;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #0284c7; margin: 0;">🌊 FloodGuard AI</h2>
            <p style="color: #64748b; font-size: 14px;">Community Emergency Flood Response</p>
        </div>
        <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="display: inline-block; background-color: #ecfdf5; color: #059669; font-weight: bold; padding: 6px 12px; border-radius: 20px; font-size: 13px; margin-bottom: 15px;">
                ✓ INCIDENT RESOLVED
            </div>
            <h3 style="color: #0f172a; margin-top: 0;">Dear {problem['name']},</h3>
            <p style="color: #334155; line-height: 1.6;">
                Good news! Your reported flood incident has been assessed and marked as <strong>COMPLETED</strong> by our emergency team.
            </p>
            <div style="background-color: #f1f5f9; padding: 15px; border-radius: 6px; margin: 20px 0;">
                <p style="margin: 4px 0; color: #475569; font-size: 14px;"><strong>Complaint ID:</strong> FG{problem['id']}</p>
                <p style="margin: 4px 0; color: #475569; font-size: 14px;"><strong>Title:</strong> {problem['title']}</p>
                <p style="margin: 4px 0; color: #475569; font-size: 14px;"><strong>Location:</strong> {problem['location']}</p>
            </div>
            <div style="border-left: 4px solid #0284c7; padding-left: 12px; margin: 20px 0;">
                <h4 style="margin: 0 0 6px 0; color: #0284c7;">Agent Resolution Remarks:</h4>
                <p style="margin: 0; color: #334155; font-style: italic; white-space: pre-wrap;">{problem['remarks']}</p>
            </div>
            <p style="color: #64748b; font-size: 13px; margin-top: 25px;">
                Thank you for your active participation in making our streets and neighborhoods safer.
            </p>
        </div>
        <div style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 15px;">
            &copy; FloodGuard AI Rapid Response System
        </div>
    </div>
    """

    try:
        mail.send(msg)
        return True
    except Exception as error:
        current_app.logger.exception("Gmail delivery failed")
        raise RuntimeError(f"Gmail SMTP error: {error}") from error
