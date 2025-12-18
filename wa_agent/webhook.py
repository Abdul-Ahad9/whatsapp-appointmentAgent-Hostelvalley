import os 
import json
from datetime import datetime
from fastapi import Query, Request, Response
from .utilities import (
    send_whatsapp_message,
    extract_location_and_city,
    fetch_data_from_api
)
from .utilities import client
# from .bot_logic import handle_user_message
from .chat_logic import check_and_get_customer_summary, generate_gemini_response, handle_user_message

from ..redis_client import session_mgr
from .chat_logger import logger

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "meta_key")

async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    print(f"Verifying webhook with mode: {hub_mode}, token: {hub_verify_token} our token: {VERIFY_TOKEN}")
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("WEBHOOK VERIFIED")
        return Response(content=hub_challenge, status_code=200)
    else:
        return Response(status_code=403)

# async def receive_webhook(request: Request):
#     # body = await request.json()
#     timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
#     print(f"\n\nWebhook received {timestamp}\n")
#     # return Response(status_code=200)
#     data = await request.json()
#     print(json.dumps(data, indent=2))
#     try:
#         entry = data["entry"][0]["changes"][0]["value"]
#         messages = entry.get("messages", [])
#         if not messages:
#             return Response(status_code=200)  # ignore delivery receipts

#         message = messages[0]
#         sender = message["from"]
#         message_text = message["text"]["body"]

#         print(f"Received message: {message_text} from {sender}")

#         # Step 1: Extract city & location
#         city, location = extract_location_and_city(message_text)

#         if not city or not location:
#             reply = "Please provide both your city and specific location so I can assist you."
#             await send_whatsapp_message(sender, reply)
#             return Response(status_code=200)

#         # Step 2: Call your API
#         results = await fetch_data_from_api(city, location)

#         if results:
#             reply = f"Here are the results for {location}, {city}:\n" + json.dumps(results, indent=2)
#         else:
#             reply = f"Sorry, I couldn't find any results for {location}, {city}."

#         await send_whatsapp_message(sender, reply)
#         return Response(status_code=200)

#     except Exception as e:
#         print(f"Webhook error: {e}")
#         return Response(status_code=500)
    

async def receive_webhook(request: Request):
    data = await request.json()
    print(json.dumps(data, indent=2))
    print(f"\n\nWebhook received at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n")
    # Extract user message
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = message["from"]
        print(f"Message data: {message}")
        print(f"message type: {message['type']}")
        if message['type'] == "text":
            user_msg = message["text"]["body"]
            print(f"Received message: {user_msg} from {phone}")
        elif message['type'] == "image":
            user_chat_summary = check_and_get_customer_summary(phone, session_mgr)
            reply = await generate_gemini_response(f"""Ask user to share link, as I cannot help with images yet because it hard to find hostel from image.
                                              answer in human tone, friendly, short and just to the point, in his own language.
                                              output only in valid json,
                                              {{'reply':'your reply goes here'}}""")
            await send_whatsapp_message(phone, "text", reply['reply'])
            return {"status": "ok"}
        else:
            print(f"Unsupported message type: {message['type']}")
            return {"status": "ok"}                                  
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error"}

    try:
        # Process with logic
        bot_responses = await handle_user_message(user_msg, phone, session_mgr, logger)
        print(f"Bot responses: {bot_responses}")
    except Exception as e:
        print(f"Error in handle_user_message: {e}")
        bot_responses = [("text", "Sorry, something went wrong on our end. Please try again later.")]
        await send_whatsapp_message(phone, "text", bot_responses[0])
    # Send responses via WhatsApp
    for msg in bot_responses:
        msg_type = msg[0]
        if msg_type == "text":
            print(f"Sending text: {msg[1]}")
            await send_whatsapp_message(phone, "text", msg[1])
        elif msg_type == "image":
            await send_whatsapp_message(phone, "image", msg[1], msg[2])
            

    return {"status": "ok"}