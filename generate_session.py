"""Pyrogram String Session generate karne ke liye:  python generate_session.py"""
import asyncio
from pyrogram import Client


async def main():
    api_id = int(input("API_ID: ").strip())
    api_hash = input("API_HASH: ").strip()
    async with Client("gen", api_id=api_id, api_hash=api_hash, in_memory=True) as app:
        session = await app.export_session_string()
        print("\n✅ Aapki SESSION_STRING (kisi ko mat dena!):\n")
        print(session)
        try:
            await app.send_message("me", f"Your SESSION_STRING:\n\n`{session}`")
            print("\n(Saved Messages mein bhi bhej di gayi hai)")
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
