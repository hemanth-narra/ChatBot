from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import BadRequest
from functools import wraps
import redis
import config
import random

db = redis.Redis(host='100.117.148.71', port=6379, decode_responses=True)

bot = Client("chatbot", api_id=int(config.API_ID), api_hash=config.API_HASH)

def handle_user_is_blocked(func):
    @wraps(func)
    async def wrapped(bot, message, *args, **kwargs):
        try:
            return await func(bot, message, *args, **kwargs)
        except BadRequest as e:
            if e.status_code == 400 and "USER_IS_BLOCKED" in e.message:
                # remove the user from the partners hash map
                partner_id = db.hget("partners", message.from_user.id)
                if partner_id:
                    db.hdel("partners", message.from_user.id)
                    db.hdel("partners", partner_id)
                # remove the user from the active_users set
                db.srem("active_users", message.from_user.id)
                # send a message to the user informing them they have been removed
                await bot.send_message(message.chat.id, "You have been removed from the chat due to being blocked by the other user.")
            else:
                raise e
    return wrapped

# Define a handler for the /start command
@bot.on_message(filters.command("start"))
async def start(bot, message):
    # Add the user id to the start_users set
    db.sadd("start_users", message.from_user.id)
    # Send a text message to the user
    await bot.send_message(message.chat.id, "Type /search to find partner")

# Define a handler for the /search command
@handle_user_is_blocked
@bot.on_message(filters.command("search"))
async def search(bot, message):
    # Add the user id to the active_users set
    db.sadd("active_users", message.from_user.id)
    # Get the difference set of active_users and start_users excluding the current user id
    diff_set = db.sdiff("active_users", message.from_user.id)
    # Remove the current user id from the difference set
    diff_set.remove(str(message.from_user.id))
    # Check if there is more than one other user in the difference set
    if len(diff_set) > 0:
        # Choose a random user id from the difference set
        partner_id = random.choice(list(diff_set))
        # Store the partner id in a hash map with the current user id as key
        db.hset("partners", message.from_user.id, partner_id)
        # Store the current user id in another hash map with the partner id as key
        db.hset("partners", partner_id, message.from_user.id)
        # Send a text message to both users informing them about their match
        await bot.send_message(message.chat.id, "New Partner found\n  /next-new partner\n  /stop-stop chat")
        await bot.send_message(partner_id, "New Partner found\n  /next-new partner\n  /stop-stop chat")
        # Remove both user ids from the active_users set
        db.srem("active_users", message.from_user.id)
        db.srem("active_users", partner_id)
    else:
        # Send a text message to the user saying no match was found
        await bot.send_message(message.chat.id, "No match was found. Please try again later.")


# Define a handler for /next command
@handle_user_is_blocked
@bot.on_message(filters.command("next"))
async def next(bot, message):
    # Get the partner id of current user from hash map if it exists
    partner_id = db.hget("partners", message.from_user.id)
    if partner_id:
        # Send a text message to both users informing them about their unmatch
        await bot.send_message(message.chat.id, "New Partner found\n  /next-new partner\n  /stop-stop chat")
        await bot.send_message(partner_id, "You have been unmatched with {message.from_user.id}")
        # Delete both user ids from hash map using db.hdel() method
        db.hdel("partners", message.from_user.id)
        db.hdel("partners", partner_id)
        # Add both user ids back to active_users set using db.sadd() method
        db.sadd("active_users", message.from_user.id)
        db.sadd("active_users", partner_id)
        # Call search() function again for current user 
        await search(bot,message)


# Define handler for /stop command 
@handle_user_is_blocked
@bot.on_message(filters.command("stop"))
async def stop(bot, message):
    # Get the partner id of current user from hash map if it exists
    partner_id = db.hget("partners", message.from_user.id)
    if partner_id:
        # Send a text message to both users informing them about their unmatch
        await bot.send_message(message.chat.id, f"You have been unmatched with {partner_id}")
        await bot.send_message(partner_id, f"You have been unmatched with {message.from_user.id}")
        # Delete both user ids from hash map using db.hdel() method
        db.hdel("partners", message.from_user.id)
        db.hdel("partners", partner_id)
        # Send a text message to current user asking them to type /search to find another partner
        await bot.send_message(message.chat.id, "Type /search to find another partner")
    else:
        # Send a text message to current user saying they are not matched with anyone
        await bot.send_message(message.chat.id, "You are not matched with anyone")

# Define a handler for any other text messages (not commands)
@handle_user_is_blocked
@bot.on_message(filters.text)
async def chat(bot, message):
    # Get the partner id of the current user from the hash map if it exists
    partner_id = db.hget("partners", message.from_user.id)
    if partner_id:
        # Forward the message to the partner chat id 
        await bot.send_message(partner_id, text=message.text)
    else:
        # Send a text message to the user saying they have no partner yet
        await bot.send_message(message.chat.id, "You have no partner yet. Type /search to find one.")

@handle_user_is_blocked
@bot.on_message(filters.video)
async def chat(bot, message):
    # Get the partner id of the current user from the hash map if it exists
    partner_id = db.hget("partners", message.from_user.id)
    if partner_id:
        # Forward the message to the partner chat id 
        await bot.send_video(partner_id, video=message.video.file_id)
    else:
        # Send a text message to the user saying they have no partner yet
        await bot.send_message(message.chat.id, "You have no partner yet. Type /search to find one.")

@handle_user_is_blocked
@bot.on_message(filters.photo)
async def chat(bot, message):
    # Get the partner id of the current user from the hash map if it exists
    partner_id = db.hget("partners", message.from_user.id)
    if partner_id:
        # Forward the message to the partner chat id 
        await bot.send_photo(partner_id, photo=message.photo.file_id)
    else:
        # Send a text message to the user saying they have no partner yet
        await bot.send_message(message.chat.id, "You have no partner yet. Type /search to find one.")

@handle_user_is_blocked
@bot.on_message(filters.sticker)
async def chat(bot, message):
    # Get the partner id of the current user from the hash map if it exists
    partner_id = db.hget("partners", message.from_user.id)
    if partner_id:
        # Forward the message to the partner chat id 
        await bot.send_photo(partner_id, sticker=message.sticker.file_id)
    else:
        # Send a text message to the user saying they have no partner yet
        await bot.send_message(message.chat.id, "You have no partner yet. Type /search to find one.")

@handle_user_is_blocked
@bot.on_message(filters.document)
async def chat(bot, message):
    # Get the partner id of the current user from the hash map if it exists
    partner_id = db.hget("partners", message.from_user.id)
    if partner_id:
        # Forward the message to the partner chat id 
        await bot.send_document(partner_id, document=message.document.file_id)
    else:
        # Send a text message to the user saying they have no partner yet
        await bot.send_message(message.chat.id, "You have no partner yet. Type /search to find one.")

# Start running the bot 
if __name__=='__main__':
    bot.run()