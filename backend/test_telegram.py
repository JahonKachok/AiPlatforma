"""
Telegram bot integration test script
Run: python test_telegram.py
"""

import asyncio
from app.services.telegram_service import telegram_service
from app.config import settings

async def test_telegram():
    print("🧪 Testing Telegram Integration...\n")

    # Initialize service
    await telegram_service.initialize()

    if not telegram_service.enabled:
        print("❌ Telegram service not enabled. Check TELEGRAM_BOT_TOKEN in .env")
        return

    print("✅ Telegram service initialized\n")

    # Get bot info
    try:
        bot_info = await telegram_service.bot.get_me()
        print(f"🤖 Bot Info:")
        print(f"   Username: @{bot_info.username}")
        print(f"   Name: {bot_info.first_name}")
        print(f"   Bot ID: {bot_info.id}\n")
    except Exception as e:
        print(f"❌ Failed to get bot info: {e}\n")
        return

    # Test sending message
    if settings.TELEGRAM_USER_ID:
        try:
            print(f"📨 Sending test message to {settings.TELEGRAM_USER_ID}...")
            success = await telegram_service.send_message(
                chat_id=settings.TELEGRAM_USER_ID,
                text="✅ <b>Telegram Bot Test</b>\n\nBu test xabaridir. Integratsiya muvaffaqiyatli ishlayapti!",
                parse_mode="HTML"
            )
            if success:
                print("✅ Message sent successfully!\n")
            else:
                print("❌ Failed to send message\n")
        except Exception as e:
            print(f"❌ Error sending message: {e}\n")

        # Test task notification
        try:
            print("📋 Sending task notification...")
            success = await telegram_service.send_task_notification(
                chat_id=settings.TELEGRAM_USER_ID,
                task_title="Test Vazifasi",
                task_id="12345",
                action="yaratildi"
            )
            if success:
                print("✅ Task notification sent successfully!\n")
            else:
                print("❌ Failed to send task notification\n")
        except Exception as e:
            print(f"❌ Error sending task notification: {e}\n")

        # Test deadline reminder
        try:
            print("⚠️ Sending deadline reminder...")
            success = await telegram_service.send_deadline_reminder(
                chat_id=settings.TELEGRAM_USER_ID,
                title="Loyiha Muddati",
                deadline="2024-12-31"
            )
            if success:
                print("✅ Deadline reminder sent successfully!\n")
            else:
                print("❌ Failed to send deadline reminder\n")
        except Exception as e:
            print(f"❌ Error sending deadline reminder: {e}\n")
    else:
        print("⚠️ TELEGRAM_USER_ID not configured in .env\n")

    print("🎉 Tests completed!")

if __name__ == "__main__":
    asyncio.run(test_telegram())
