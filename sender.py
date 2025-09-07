from telethon.sync import TelegramClient
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, InviteHashExpiredError, InviteHashInvalidError
import time
import re

api_id =        
api_hash = ''    

client = TelegramClient('+37362051696', api_id, api_hash)

def parse_invite_link(link):
    """Парсит ссылку и возвращает username или хэш приглашения"""
    # Для публичных чатов (https://t.me/username)
    if link.startswith('https://t.me/'):
        parts = link.split('/')
        if len(parts) >= 4 and parts[3]:
            return parts[3]  # Возвращаем username без @
    
    # Для приватных чатов (https://t.me/+invitehash)
    if link.startswith('https://t.me/+'):
        return link.split('+')[1]  # Возвращаем хэш приглашения
    
    return None

async def join_chat(link):
    """Функция для вступления в чат/канал по ссылке"""
    try:
        identifier = parse_invite_link(link)
        if not identifier:
            print(f"❌ Неверный формат ссылки: {link}")
            return False

        # Для публичных чатов
        if not identifier.startswith('+'):
            await client(JoinChannelRequest(identifier))
            return True
        
        # Для приватных чатов с хэшем приглашения
        else:
            await client(ImportChatInviteRequest(identifier))
            return True
            
    except FloodWaitError as e:
        print(f"⏱ FloodWait на {e.seconds} секунд при вступлении, спим...")
        time.sleep(e.seconds)
        return False
    except (InviteHashExpiredError, InviteHashInvalidError):
        print(f"❌ Недействительная или просроченная ссылка: {link}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при вступлении в {link}: {e}")
        return False

async def main():
    await client.start()

    with open("template.txt", "r", encoding="utf-8") as f:
        template = f.read()

    with open("users.txt", "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    for link in links:
        try:
            # Пытаемся вступить в чат/канал
            success = await join_chat(link)
            if not success:
                continue
                
            # Получаем сущность после успешного вступления
            identifier = parse_invite_link(link)
            if identifier.startswith('+'):
                # Для приватных чатов нужно получить entity по ID
                # (это сложнее, можно пропустить или найти другой способ)
                print(f"⚠️ Отправка в приватные чаты по ссылке может потребовать дополнительной обработки: {link}")
                continue
                
            entity = await client.get_entity(identifier)
            message = template.replace("{username}", identifier)
            
            # Отправляем сообщение
            await client.send_message(entity, message)
            print(f"✅ Сообщение отправлено в {link}")
            time.sleep(50)

        except UserPrivacyRestrictedError:
            print(f"🔒 Пользователь/чат ограничил ЛС: {link}")
        except FloodWaitError as e:
            print(f"⏱ FloodWait на {e.seconds} секунд при отправке, спим...")
            time.sleep(e.seconds)
        except Exception as e:
            print(f"❌ Ошибка с {link}: {e}")

    await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())