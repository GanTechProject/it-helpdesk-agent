# Copyright 2026 Google LLC
# Seed script for Firestore support_tickets and knowledge_base collections

from google.cloud import firestore

# CRITICAL: Hardcode the project ID string (ID, not number)
FIRESTORE_PROJECT = "qwiklabs-gcp-01-4aae627fbb97"

def seed_database():
    print(f"Connecting to Firestore in project '{FIRESTORE_PROJECT}'...")
    db = firestore.Client(project=FIRESTORE_PROJECT)

    # 1. Seed Support Tickets
    tickets_ref = db.collection("support_tickets")
    tickets = [
        {
            "ticket_id": "TCK-1001",
            "user_email": "alex.smith@company.com",
            "device_info": "MacBook Pro 16-inch (M2)",
            "title": "VPN Connection Failure",
            "description": "Unable to connect to corporate VPN when working remotely on home Wi-Fi network.",
            "category": "Network",
            "status": "Open",
            "priority": "High",
            "created_at": "2026-09-24 08:30:00 UTC",
        },
        {
            "ticket_id": "TCK-1002",
            "user_email": "sarah.chen@company.com",
            "device_info": "Dell XPS 15 (Windows 11)",
            "title": "Monitor flickering on Docking Station",
            "description": "External dual monitor flickers randomly when plugged into USB-C docking station.",
            "category": "Hardware",
            "status": "In Progress",
            "priority": "Medium",
            "created_at": "2026-09-23 14:15:00 UTC",
        },
        {
            "ticket_id": "TCK-1003",
            "user_email": "alex.smith@company.com",
            "device_info": "MacBook Pro 16-inch (M2)",
            "title": "Slack Password Reset",
            "description": "Password reset request for corporate Slack workspace after account lockout.",
            "category": "Access",
            "status": "Resolved",
            "priority": "Low",
            "created_at": "2026-09-20 10:00:00 UTC",
        },
        {
            "ticket_id": "TCK-1004",
            "user_email": "jordan.lee@company.com",
            "device_info": "Lenovo ThinkPad T14",
            "title": "Docker License Renewal",
            "description": "Docker Desktop enterprise license expired today. Need key update.",
            "category": "Software",
            "status": "Open",
            "priority": "High",
            "created_at": "2026-09-24 09:00:00 UTC",
        },
    ]

    for item in tickets:
        tickets_ref.document(item["ticket_id"]).set(item)
        print(f"Seeded ticket {item['ticket_id']}: {item['title']}")

    # 2. Seed Knowledge Base Articles
    kb_ref = db.collection("knowledge_base")
    kb_articles = [
        {
            "article_id": "KB-101",
            "title": "VPN Setup & Troubleshooting Guide",
            "category": "Network",
            "tags": ["vpn", "network", "remote", "connect"],
            "summary": "Steps to resolve GlobalProtect / Cisco VPN connection issues.",
            "content": (
                "1. Verify home Wi-Fi connection and ensure no captive portal is blocking access.\n"
                "2. Open VPN client settings, set gateway to 'vpn.company.com', and verify certificate validity.\n"
                "3. Flush DNS cache:\n"
                "   - macOS: sudo killall -HUP mDNSResponder\n"
                "   - Windows: ipconfig /flushdns\n"
                "4. Restart the VPN background service if authentication times out."
            ),
        },
        {
            "article_id": "KB-102",
            "title": "Password Reset & Account Unlocking Procedures",
            "category": "Access",
            "tags": ["password", "reset", "sso", "lockout", "account"],
            "summary": "Self-service instructions for resetting corporate SSO passwords.",
            "content": (
                "1. Visit https://sso.company.com/reset-password from any browser or mobile device.\n"
                "2. Enter your corporate email and approve the 2FA prompt on Okta/Duo.\n"
                "3. Create a new password adhering to standards (16+ chars, uppercase, lowercase, numbers, symbols).\n"
                "4. Update your stored password in macOS Keychain / Windows Credential Manager."
            ),
        },
        {
            "article_id": "KB-103",
            "title": "USB-C Docking Station & External Display Troubleshooting",
            "category": "Hardware",
            "tags": ["monitor", "display", "dock", "usb-c", "flickering"],
            "summary": "Fixing flickering monitors, resolution glitches, or hub power issues.",
            "content": (
                "1. Unplug the USB-C docking station power cable for 10 seconds to power-cycle the firmware.\n"
                "2. Ensure DisplayLink drivers are updated to the latest version (v11.x+).\n"
                "3. In System Settings -> Displays, set refresh rate to 60Hz instead of Variable/Adaptive.\n"
                "4. Test using a single DisplayPort cable to rule out faulty adapters."
            ),
        },
        {
            "article_id": "KB-104",
            "title": "Requesting Software Licenses (Docker, IntelliJ, Figma)",
            "category": "Software",
            "tags": ["software", "license", "docker", "approval", "install"],
            "summary": "How to request developer licenses and paid software tool access.",
            "content": (
                "1. Submit a license request via the IT Self-Service Portal under 'Software Provisioning'.\n"
                "2. Manager approval is automatically routed for licenses exceeding $50/month.\n"
                "3. Once approved, key license strings are dispatched via IT Security Vault within 2 hours."
            ),
        },
    ]

    for article in kb_articles:
        kb_ref.document(article["article_id"]).set(article)
        print(f"Seeded KB article {article['article_id']}: {article['title']}")

    print("Firestore database successfully seeded!")

if __name__ == "__main__":
    seed_database()
