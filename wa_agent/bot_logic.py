# chatbot_logic.py
import os, json
import requests
import google.generativeai as genai
from ..redis_client import SessionManager
from .utilities import extract_location_and_city, send_whatsapp_message


from .chat_logger import ChatLogger

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

HOSTEL_SEARCH_URL = "https://hostelvalley.com/api/v1/hostels"
HOSTEL_DETAILS_URL = "https://hostelvalley.com/api/v1/hostels"

async def get_intent(message: str) -> str:
    prompt = f"""
    Determine the intent of the following user message. 
    Possible intents are: "greeting", "search_hostel", "book_hostel", "time_waster","or whatever you detect".
    User message: "{message}"
    """
    response = model.generate(
        prompt=prompt,
        max_output_tokens=50,
        temperature=0.0,
        top_p=0.8,
        top_k=40,
        stop_sequences=["\n"]
    )
    intent = response.text.strip().lower()
    # if intent in [///"greeting", "search_hostel", "book_hostel"]:
    #     return intent
    # return "other"
    return intent



async def handle_booking_step(step, msg, phone, session_mgr, logger):
    session = await session_mgr.get_session(phone)

    if step == "ask_hostel":
        session["hostel"] = msg
        session["booking_step"] = "ask_date"
        await session_mgr.set_session(phone, session)
        return "Great! When would you like to check in?"

    elif step == "ask_date":
        session["date"] = msg
        session["booking_step"] = "ask_name"
        await session_mgr.set_session(phone, session)
        return "Got it. What’s your full name?"

    elif step == "ask_name":
        session["name"] = msg
        session["booking_step"] = "ask_phone"
        await session_mgr.set_session(phone, session)
        return "Lastly, your contact number?"

    elif step == "ask_phone":
        session["user_phone"] = msg
        session["booking_step"] = None
        await session_mgr.clear_session(phone)

        await logger.log_message(phone, f"Booking: {session}", is_user=False)
        return (
            f"✅ Booking confirmed for {session['hostel']} on {session['date']}!\n"
            f"We'll reach out to {session['user_phone']} if needed. Thank you, {session['name']}!"
        )


async def handle_user_message(user_msg: str, phone: str, session_mgr: SessionManager, logger: ChatLogger):
    # 1. Greeting detection via Gemini intent
    intent = get_intent(user_msg)

    if intent == "greeting":
        reply = "Hey there! 😊 How can I help you find the perfect hostel today?"
        await send_whatsapp_message(phone, reply)
        await logger.log_message(phone, user_msg, True)
        await logger.log_message(phone, reply, False)
        return [("text", reply)]
    
    if intent == "time_waster":
        reply = "I'm here to help with hostel bookings. How can I assist you today?"
        await send_whatsapp_message(phone, reply)
        await logger.log_message(phone, user_msg, True)
        await logger.log_message(phone, reply, False)
        return [("text", reply)]
    
    # if intent == "book_hostel":
    #     session = await session_mgr.get_session(phone)
    #     session["booking_step"] = "ask_hostel"
    #     await session_mgr.set_session(phone, session)
    #     reply = "Sure! Which hostel would you like to book?"
    #     await send_whatsapp_message(phone, reply)
    #     await logger.log_message(phone, user_msg, True)
    #     await logger.log_message(phone, reply, False)
    #     return [("text", reply)]    
    
    # if intent == "search_hostel":
    #     reply = "Got it! Please provide the city and location you're interested in."
    #     await send_whatsapp_message(phone, reply)
    #     await logger.log_message(phone, user_msg, True)
    #     await logger.log_message(phone, reply, False)
    #     return [("text", reply)]
    
    # if intent not in ["search_hostel", "book_hostel", "greeting", "time_waster"]:
    #     recent = await logger.get_recent_messages(phone, limit=6)
    #     history_str = "\n".join(
    #     [f"{'User' if m['is_from_user'] else 'Bot'}: {m['content']}" for m in recent]
    #     )
    #     prompt = (
    #     "You are a friendly assistant for HostelValley.com.\n"
    #     "Your job is to help users find the best hostel based on their location, budget, and preferences.\n"
    #     "Use a helpful and natural tone keeping it short.\n\n"
    #     f"Conversation so far:\n{history_str}\n\n"
    #     f"User: {user_msg}\n"
    #     "Assistant:"
    #     )

    #     try:
    #     response = model.generate_content(prompt)
    #     reply = response.text.strip()
    #     await send_whatsapp_message(phone, reply)
    #     except Exception as e:
    #         reply = "Sorry, I couldn't understand that. Could you please elaborate better?"
    #         await send_whatsapp_message(phone, reply)
    #     # 4. Log both messages
    #     await logger.log_message(phone, user_msg, is_user=True)
    #     await logger.log_message(phone, reply, is_user=False)
    #     return reply

    # 2. See if booking flow is ongoing
    session = await session_mgr.get_session(phone)
    if session.get("booking_step"):
        # handle booking steps...
        # (similar to earlier booking flow code)
        reply = await handle_booking_step(session["booking_step"], user_msg, phone, session_mgr, logger)
        pass

    # 3. Extract city & location using your existing function
    city, location = extract_location_and_city(user_msg)

    if city and location:
        # 4. Query search API
        resp = requests.get(HOSTEL_SEARCH_URL, params={"city": city, "location": location, "gender": "", "radius": "1"})
        hostels = resp.json().get("results", [])

        if not hostels:
            reply_text = f"Sorry, I couldn't find any hostels in {location}, {city}."
            await logger.log_message(phone, user_msg, True)
            await logger.log_message(phone, reply_text, False)
            await send_whatsapp_message(phone, reply_text)
            return [("text", reply_text)]

        # 5. Send up to 3 hostels with thumbnails
        messages = []
        reply_text = f"Here are some hostels in {location}, {city}:"
        messages.append(("text", reply_text))

        for hostel in hostels[:3]:
            image_url = hostel.get("thumbnail")
            caption = f"{hostel['name']} — {hostel.get('price', 'Price N/A')}"
            messages.append(("image", image_url, caption))

        messages.append(("text", "Let me know if you’d like to book one or see more details!"))
        await logger.log_message(phone, user_msg, True)
        await send_whatsapp_message(phone, reply_text)
        for m in messages:
            await logger.log_message(phone, m[2] if m[0]=="image" else m[1], False)
        return messages

    # 6. Default fallback
    reply = "Could you please tell me the city or neighbourhood you're looking in for a hostel?"
    await logger.log_message(phone, user_msg, True)
    await logger.log_message(phone, reply, False)
    return [("text", reply)]



