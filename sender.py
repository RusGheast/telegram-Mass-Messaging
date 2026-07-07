from telethon import TelegramClient
from telethon.network import connection
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, InviteHashExpiredError, InviteHashInvalidError
from dotenv import load_dotenv
import time
import asyncio
import os

load_dotenv()

number = os.getenv('number')
api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')

PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = int(os.getenv('PROXY_PORT'))
PROXY_SECRET = os.getenv('PROXY_SECRET')

TEMPLATE_FILE = "template.txt"
USERS_FILE = "users.txt"
PHOTO_FILE = "photo.png"

def parse_invite_link(link):
    """Парсит ссылку и возвращает username или хэш приглашения"""
    if link.startswith('https://t.me/'):
        parts = link.split('/')
        if len(parts) >= 4 and parts[3]:
            return parts[3]
    if link.startswith('https://t.me/+'):
        return link.split('+')[1]
    return None

def create_client_with_proxy():
    """Создает клиент с MTProto-прокси через класс MTProtoProxy"""
    try:
        secret_bytes = bytes.fromhex(PROXY_SECRET)
    except ValueError:
        print("❌ Ошибка: секрет должен быть hex-строкой")
        raise

    # Явно указываем класс подключения и передаём параметры прокси
    client = TelegramClient(
        number,
        api_id,
        api_hash,
        proxy=(PROXY_HOST, PROXY_PORT, PROXY_SECRET),  # для MTProtoProxy используется кортеж (host, port, secret)
        connection=connection.ConnectionTcpMTProxyAbridged
    )
    print(f"🔌 Используем MTProto-прокси: {PROXY_HOST}:{PROXY_PORT}")
    return client

async def join_chat(client, link):
    try:
        identifier = parse_invite_link(link)
        if not identifier:
            print(f"❌ Неверный формат ссылки: {link}")
            return False
        if not identifier.startswith('+'):
            await client(JoinChannelRequest(identifier))
        else:
            await client(ImportChatInviteRequest(identifier))
        return True
    except FloodWaitError as e:
        print(f"⏱ FloodWait на {e.seconds} секунд, спим...")
        await asyncio.sleep(e.seconds)
        return False
    except (InviteHashExpiredError, InviteHashInvalidError):
        print(f"❌ Недействительная ссылка: {link}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при вступлении: {e}")
        return False

async def send_message_with_photo(client, entity, message, photo_path=None):
    try:
        if photo_path and os.path.exists(photo_path):
            await client.send_file(entity, photo_path, caption=message)
            print("✅ Сообщение с фото отправлено")
        else:
            await client.send_message(entity, message)
            print("✅ Текстовое сообщение отправлено")
        return True
    except FloodWaitError as e:
        print(f"⏱ FloodWait на {e.seconds} секунд, спим...")
        await asyncio.sleep(e.seconds)
        return False
    except UserPrivacyRestrictedError:
        print("🔒 Пользователь/чат ограничил ЛС")
        return False
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")
        return False

async def process_links(client):
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ Файл {TEMPLATE_FILE} не найден")
        return
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    if not os.path.exists(USERS_FILE):
        print(f"❌ Файл {USERS_FILE} не найден")
        return
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]
    if not links:
        print("⚠️ Список ссылок пуст")
        return

    photo_path = PHOTO_FILE if os.path.exists(PHOTO_FILE) else None

    print(f"🔄 Обработка {len(links)} ссылок...")
    for i, link in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] {link}")

        success = await join_chat(client, link)
        if not success:
            continue

        identifier = parse_invite_link(link)
        try:
            entity = await client.get_entity(link) if identifier.startswith('+') else await client.get_entity(identifier)
        except Exception as e:
            print(f"⚠️ Не удалось получить entity: {e}")
            continue

        message = template.replace("{username}", identifier)
        await send_message_with_photo(client, entity, message, photo_path)

        if i < len(links):
            print("⏳ Пауза 50 секунд...")
            await asyncio.sleep(50)

async def main():
    client = create_client_with_proxy()
    await client.start()
    print("✅ Клиент запущен, цикл каждые 15 минут. Нажмите Ctrl+C для остановки.")

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n{'='*50}")
            print(f"🔄 ЦИКЛ #{cycle} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")
            await process_links(client)
            print(f"\n✅ Цикл #{cycle} завершён. Ожидание 15 минут...")
            await asyncio.sleep(900)
    except KeyboardInterrupt:
        print("\n🛑 Остановка пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        await client.disconnect()
        print("👋 Отключено")

if __name__ == "__main__":
    asyncio.run(main())