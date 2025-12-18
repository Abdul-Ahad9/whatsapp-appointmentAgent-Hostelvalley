# chatbot_logic.py
import google.generativeai as genai
import os, json
import aiohttp
from .chat_logger import logger
import random

# A LOGIC THOUGHT:
#    is it any good if we keep an extract of customer, a comprehensive summary of chat history
#    in db, so that we can use it to prompt gpt for better responses?

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


async def generate_gemini_response(prompt: str) -> dict:
    response = model.generate_content(prompt)
        # prompt=prompt
        # max_output_tokens=550,
        # temperature=0.7,
        # top_p=0.8,
        # top_k=40,
        # stop_sequences=["\n"]
    # )
    print(f"[Gemini] Raw response: {response.text}")
    try:
        content = response.text.strip().strip("```json").strip("```").strip()
        print(f"[Gemini] Cleaned content: {content}")
        json_block = json.loads(content)
        print(f"[Gemini] Parsed JSON: {json_block}")
        return json_block
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {
            "intent": "unknown",
            "entities": {},
            "reply": "Sorry, I didn’t quite get that. Could you rephrase?"
        }
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            "intent": "unknown",
            "entities": {},
            "reply": "Sorry, I didn’t quite get that. Could you rephrase?"
        }
    return {
        "intent": "unknown",
        "reply": "Sorry, I didn’t quite get that. Could you rephrase?"
    }
async def get_gemini_response(user_msg: str) -> dict:
    # with open("prompts/gemini_prompt.txt") as f:
    #     base_prompt = f.read()

    base_prompt = '''You are a friendly assistant for HostelValley helping customers find and book hostels.
        Your job is to:
        - Detect the user's intent: greeting, search, booking, question, unknown
        - Extract helpful info: city, location, gender, price_range, name, date, hostel name
        - Provide a friendly, helpful reply, but keep it short unless longer is needed.
        - Output valid JSON

        Always return your response as:
        {
        "intent": "search" | "booking" | "greeting" | "smalltalk" | "unknown",
        "entities": {
            "city": null | "Islamabad",
            "location": null | "F-8",
            "gender": null | "Girls",
            "price_range": null | "15000",
            "hostel": null | "SS Girls Hostel",
            "name": null | "Ayesha",
            "date": null | "2024-08-22"
            "education": null | "intermediate/Graduate/etc"
            "student": "null | "yes/no"
            "occupation" : "null | "Driver" (this is required only if student = no)
        },
        "reply": "Your human-sounding, friendly reply goes here."
        }

        you can extract city from location if needed, with your own knowledge.
        increase price_range if user is asking for more expensive hostels than his range.
        Note: reply in whatever language user has sent the message in, be it urdu in english wording etc.
        '''

    prompt = f"{base_prompt}\n\nUser: {user_msg}"

    print(f"[Gemini] Prompt: {prompt}")

    try:
        response = model.generate_content(prompt)
        print(f"[Gemini] Raw response: {response.text}")
        content = response.text.strip().strip("```json").strip("```").strip()
        json_block = json.loads(content)
        print(f"[Gemini] Response: {json_block}")
        return json_block
    except Exception as e:
        print(f"[Gemini Error]: {e}")
        return {
            "intent": "unknown",
            "entities": {},
            "reply": "Sorry, I didn’t quite get that. Could you rephrase?"
        }
    return {
    "intent": "unknown",
    "reply": "Sorry, I didn’t quite get that. Could you rephrase?"
    }


async def update_summary(phone, old_summary, new_user_message, new_bot_reply, session_mgr):
    try:
        new_summary = await generate_gemini_response(f"""Previous chat summary was, summary:'{old_summary}', new user message is, message:'{new_user_message}',
                                            and my reply is: '{new_bot_reply}',
                                            if there is any important information in any either user message or my reply, log it properly with full details 
                                            as the user can ask for it later,
                                            old summary is already comprehensive, so only update it if there is something new to add,
                                            you can also remove redundant information if needed and modify old summary it is already too long(more than 1000 words),
                                            Output a valid JSON object with this structure: 
                                                                {{
                                                                "summary": "Your human-sounding summary goes here."
                                                                }}""")
        update_summary_in_db = await logger.update_summary(phone, new_summary.get("summary"))
        update_summary_in_redis = await session_mgr.update_chat_summary(phone, new_summary.get("summary"))
        return True
    except Exception as e:
        print(f"[error setting summary]: {e}")
        return False


async def check_and_get_customer_data(phone, session_mgr, **args):
    try:
        redis_session = await session_mgr.get_session(phone)
        print(f"Redis session for {phone}: {redis_session}")    
        if redis_session:
            user_Data = {
                "name":redis_session.get('name'),
                "education": redis_session.get('education'),
                "student":redis_session.get('student'),
                "occupation":redis_session.get('occupation'),
                "city":redis_session.get('city'),
                "location":redis_session.get('location'),
                "price_range":redis_session.get('price_range'),
                "hostel":redis_session.get('hostel'),
                "date":redis_session.get('date'),

            }
            print(f"user data found in redis: {user_Data}")
            missing_fields = [key for key, value in user_Data.items() if not value]
            if not missing_fields:
                return {
                    "status":"complete",
                    "user_data":user_Data}
            else:
                return {
                    "status": "incomplete",
                    "data": user_Data,
                    "missing_data":missing_fields}
            # fields = ["name", "education", "student", "occupation", "city", "location", "price_range", "hostel", "date"]
            # missing = [f for f in fields if not redis_session.get(f)]
            # if missing:
            #     print(f"Missing fields for {phone}: {missing}")
            #     return (f"Ask user following fields: {', '.join(missing)} for better search", False)
        db_data = await logger.get_recent_messages(phone)
        if db_data is not None:
            return {
                "status":"fallback",
                    "msg_logs":db_data}
        return {
            "status":"new_customer",
            "data":""
        }
    except Exception as e:
        print(f"Error inside check_customer_data: {e}")
        return {
            "status": "error",
            "data": str(e)
        }


async def check_and_get_customer_summary(phone, session_mgr, **args):
    try:
        chat_summary = await session_mgr.get_chat_summary(phone)
        print(f"Chat summary for {phone}: {chat_summary}")
        if chat_summary:
            return {
                "status":"incomplete",
                "data":chat_summary
            }
        if not chat_summary:
            db_data = await logger.get_latest_summary(phone)
            if db_data is not None:
                return {
                    "status":"fallback",
                    "data":db_data
                }
        return {
            "status":"new_customer",
            "data":""
        }
    
    except Exception as e:
        print(f"Error inside check_customer_summary: {e}")
        return {
            "status": "error",
            "data": str(e)
        }
    
    

async def handle_hostel_search(phone, entities, logger, gemini_reply, session_mgr):
    try:
        city = entities.get("city")
        location = entities.get("location")
        gender = entities.get("gender") or ""
        price_range = entities.get("price_range") or ""
        radius = 1

        if not city or not location:
            return [("text", "Can you please tell me the city and area you're looking in?")]

        # Query your hostel API
        url = "https://hostelvalley.com/api/v1/hostels"
        params = {
            "city": city,
            "location": location,
            "gender": gender,
            "radius": radius,
            "price_range": price_range,
        }
        print(f"Searching hostels with params: {params}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    print(f"Hostel API response: {data}")
                    hostels = data.get("data", {}).get("hostels", [])
                    if not hostels:
                        msg = f"Sorry, I couldn’t find hostels in {location}, {city}. Want to try another area?"
                        await logger.log_message(phone, msg, is_user=False)
                        return [("text", msg)]


                    selected_hostels = random.sample(hostels, min(3, len(hostels)))


                    # Format each hostel
                    formatted = []
                    formatted.append(("text", gemini_reply))
                    for h in selected_hostels:
                        name = h.get("name", "Unnamed Hostel")
                        price = h.get("price", "N/A")
                        city = h.get("city", "").lower().replace(" ", "-")
                        slug = h.get("slug", "")
                        link = f"https://hostelvalley.com/hostels/{city}/{slug}"
                        hostel_str = f"Check these {name} - Rs {price}/month\n{link}"
                        # formatted.append(f"Check these \n {name} - Rs {price}/month\n{link}")
                        formatted.append(("text", hostel_str))
                    chat_summary = await check_and_get_customer_summary(phone, session_mgr)
                    await update_summary(phone, chat_summary.get("data"), gemini_reply, "\n".join([f[1] for f in formatted]), session_mgr)
                    return formatted
        except Exception as e:
            print(f"Error calling hostel API: {e}")
            return [("text", "Sorry, I’m having trouble accessing the hostel data right now. Please try again later.")]
        # No hostels found
        if not hostels:
            msg = f"Sorry, I couldn’t find hostels in {location}, {city}. Want to try another area?"
            await logger.log_message(phone, msg, is_user=False)
            return [("text", msg)]

        # Create a friendly intro
        results = [("text", gemini_reply)]
        for hostel in hostels[:3]:
            caption = f"🏡 {hostel['name']}\nStarts from Rs. {hostel.get('price', 'N/A')}"
            image_url = hostel.get("thumbnail")
            results.append(("image", image_url, caption))

        results.append(("text", "Would you like to book one of these or see more details?"))
        print(f"here are some results {results}")
        for msg in results:
            await logger.log_message(phone, msg[2] if msg[0] == "image" else msg[1], is_user=False)
        return results
    except Exception as e:
        print(f"Error inside handle_hostel_search: {e}")
        return [("text", "Please try again later.")]

async def handle_booking_flow(phone, user_msg, session_mgr, logger, entities):
    session = await session_mgr.get_session(phone)
    print(f"Current booking session for {phone}: {session}")
    # Collect missing details in order
    for field in ["hostel", "date", "name"]:
        if not session.get(field) and entities.get(field):
            session[field] = entities[field]
            await session_mgr.update_session(phone, {field: entities[field]})
    
    # Ask for missing fields
    if not session.get("hostel"):
        return [("text", "Which hostel would you like to book?")]
    if not session.get("date"):
        return [("text", "On which date would you like to check in?")]
    if not session.get("name"):
        return [("text", "Can I have your name for the booking?")]

    # All fields collected — simulate booking
    reply = f"🎉 Thank you {session['name']}! I’ve noted your booking request for '{session['hostel']}' on {session['date']}. Our team will confirm it shortly."
    await logger.log_message(phone, reply, is_user=False)
    await session_mgr.clear_session(phone)
    return [("text", reply)]



async def handle_user_message(user_msg, phone, session_mgr, logger):
    try:
        # if user_msg.
        # user_data = await check_and_get_customer_data(phone, session_mgr)
        user_data = await check_and_get_customer_summary(phone, session_mgr)
        status = user_data.get('status')
        data = user_data.get("data")

        if status == "complete":
            print(status)
            print("going to handle_booking_flow")
            return await handle_booking_flow()

        elif status == "incomplete":
            print(status)
            base_prompt = '''You are a friendly and humanly customer service representative for HostelValley helping customers find and book hostels.
        Your job is to:
        - Detect the user's intent: greeting, search, booking, question, unknown, from New_message only
        - Extract helpful info: city, location, gender, price_range, name, date, hostel name
        - Provide a friendly, helpful reply, but keep it short unless longer is needed.
        - Output valid JSON

        Always return your response as:
        {
        "intent": "search" | "booking" | "greeting" | "smalltalk" | "unknown" | "query",
        "entities": {
            "city": null | "Islamabad",
            "location": null | "F-8",
            "gender": null | "Boys/Girls",
            "price_range": null | "15000",
            "hostel": null | "SS Girls Hostel",
            "name": null | "Ayesha",
            "date": null | "2025-08-22"
            "education": null | "intermediate/Graduate/etc"
            "student": "null | "yes/no"
            "occupation" : "null | "Driver" (this is required only if student = no)
        },
        "reply": "Your human-sounding, friendly reply goes here."
        }
        you can extract city from location with your own knowledge, if needed and location can only be one word.
        you can book hostel if all details are present in Existing Data.
        if user has query regarding hostel and hostel details are present in Existing Data, ask user to check details on the link provided.
        If user has any query other than a hostel, answer it yourself if possible or ask user to wait and you will connect them to a human agent and make intent the "query".
        Only use the New_message to determine intent, and use new_message + chat_log + Existing Data to generate reply.
        Only use Existing Data when intent is "search" or "booking" or "query" to fill in missing details, dont include Existing data when 
        determining intent.
        Note: reply in whatever language user has sent the message in, be it urdu in english style etc, keep answer short ant to the point.
        '''
            # chat_log = await session_mgr.get_chat_history(phone)
            # print(f"chat log: {chat_log}")
            # prompt = f"{base_prompt}\n\nNew_message: {user_msg}\n\nChat_log: {chat_log}, Existing Data: {json.dumps(user_data.get('data'))}\n\nNow generate your response."
            prompt = f"{base_prompt}\n\n new_message: {user_msg}, overall chat summary looking at previous chats:{data}\n\nNow generate your response."
            ai_response = await generate_gemini_response(prompt)
            reply = ai_response.get("reply")
            print(reply)

            print(f"Handling message from {phone}: {user_msg}")
            intent = ai_response.get("intent", "unknown")
            entities = ai_response.get("entities", {})


           
            print(f"[Gemini] Intent: {intent}, Entities: {entities}")


            try:
                # Store entities in Redis
                await session_mgr.update_session(phone, entities)
            except Exception as e:
                print(f"Error updating session: {e}")

            try:
                # Hostel Search
                if intent == "search" and entities.get("city") and entities.get("location"):
                    await update_summary(phone, data,user_msg, reply, session_mgr)
                    await logger.log_message(phone, user_msg, is_user=True)
                    await logger.log_message(phone, reply, is_user=False)
                    await session_mgr.log_message(phone, "user", user_msg)
                    await session_mgr.log_message(phone, "bot", reply)
                    return await handle_hostel_search(phone, entities, logger, reply, session_mgr)
                
                # Booking Flow
                if intent == "booking":
                    await update_summary(phone, data,user_msg, reply, session_mgr)
                    await logger.log_message(phone, user_msg, is_user=True)
                    await logger.log_message(phone, reply, is_user=False)
                    await session_mgr.log_message(phone, "user", user_msg)
                    await session_mgr.log_message(phone, "bot", reply)
                    return await handle_booking_flow(phone, user_msg, session_mgr, logger, entities)

                if intent == "query":
                    await update_summary(phone, data,user_msg, reply, session_mgr)
                    print(f"human query encountered, from{phone}, kindly respond soon")
                    return [("text", reply)]
            except Exception as e:
                print(f"Error in handle_hostel_search: {e}")

            await update_summary(phone, data,user_msg, reply, session_mgr)         
            await logger.log_message(phone, user_msg, is_user=True)
            await logger.log_message(phone, reply, is_user=False)
            await session_mgr.log_message(phone, "user", user_msg)
            await session_mgr.log_message(phone, "bot", reply)
            return [("text", reply)]


            # return [("text", reply)]
        
        elif status == "fallback":
            print(status)
            prompt = f"""
You are a helpful assistant for HostelValley.com that helps users find and book hostels.

Below is the recent chat history with a user. Use it to:
- Understand the user's intent (e.g., search, booking, question)
- Identify any useful details like city, location, gender, hostel name, price range, date, etc.
- Provide a friendly and useful reply that helps the user continue their journey (searching or booking).
- Keep your response short unless extra explanation is needed.
- If information is missing, kindly prompt the user to provide it.

Output a valid JSON object with this structure:

{{
  "intent": "search" | "booking" | "greeting" | "smalltalk" | "unknown",
  "entities": {{
    "city": null | "Islamabad",
    "location": null | "F-8",
    "gender": null | "boys/girls",
    "price_range": null | "15000",
    "hostel": null | "SS Girls Hostel",
    "name": null | "Ayesha",
    "date": null | "2024-08-22",
    "education": null | "intermediate/graduate/etc",
    "student": null | "yes" | "no",
    "occupation": null | "Engineer"
  }},
  "reply": "Your human-sounding, friendly reply goes here."
}}

Chat history:
{data}

user message: {user_msg}

Now generate your response.
"""
            
            ai_response = await generate_gemini_response(prompt)
            entities = ai_response.get("entities", {})
            await session_mgr.update_session(phone, entities)
            await update_summary(phone, data,user_msg, reply, session_mgr) 
            await logger.log_message(phone, user_msg, is_user=True)
            await logger.log_message(phone, ai_response.get('reply'), is_user=False)
            await session_mgr.log_message(phone, "user", user_msg)
            await session_mgr.log_message(phone, "bot", ai_response.get('reply'))
            return [("text", ai_response.get('reply'))]
        elif status == "new_customer":
            print(status)
            gemini = await get_gemini_response(user_msg)
            intent = gemini.get("intent", "unknown")
            entities = gemini.get("entities", {})
            reply = gemini.get("reply", "How can I help you today?")
            chat_summary = ""
            # try:
            #     generate_summary = generate_gemini_response(prompt=f"""Summarize these, user said: {user_msg} and i replied: {reply},
            #                                                 Output a valid JSON object with this structure: 
            #                                                 {{
            #                                                 "summary": "Your human-sounding summary goes here."
            #                                                 }} """)
            #     if generate_summary:
            #         chat_summary = generate_summary.get("summary", "")
            #     if chat_summary:
            #         await logger.log_summary(phone, chat_summary)
            # except Exception as e:
            #     print(f"Error setting chat summary: {e}")
            await logger.log_summary(phone, chat_summary)
            await session_mgr.log_chat_summary(phone, chat_summary)
            await session_mgr.log_message(phone, "user", user_msg)
            await session_mgr.log_message(phone, "bot", reply)
            try:
                # Store entities in Redis
                await session_mgr.update_session(phone, entities)
            except Exception as e:
                print(f"Error updating session: {e}")
            return [("text", reply)]


            
        else:
            pass
            # Partial data present, proceed with normal flow
        


        # print(f"Handling message from {phone}: {user_msg}")
        # gemini = await get_gemini_response(user_msg)
        # print(f"Gemini response: {gemini}")
        # intent = gemini.get("intent", "unknown")
        # entities = gemini.get("entities", {})
        # reply = gemini.get("reply", "How can I help you today?")

        # city = entities.get("city")
        # location = entities.get("location")
        # gender = entities.get("gender")
        # price_range = entities.get("price_range")


        # print(f"[Gemini] Intent: {intent}, Entities: {entities}")


        # try:
        #     # Store entities in Redis
        #     await session_mgr.update_session(phone, entities)
        # except Exception as e:
        #     print(f"Error updating session: {e}")

        # # Booking Flow
        # if intent == "booking":
        #     return await handle_booking_flow(phone, user_msg, session_mgr, logger, entities)

        # try:
        #     # Hostel Search
        #     if intent == "search" and entities.get("city") and entities.get("location"):
        #         return await handle_hostel_search(phone, entities, logger, reply)
        # except Exception as e:
        #     print(f"Error in handle_hostel_search: {e}")
        # # Generic greeting or fallback
        # await logger.log_message(phone, user_msg, is_user=True)
        # await logger.log_message(phone, reply, is_user=False)
        # return [("text", reply)]
    except Exception as e:
        print(f"Error inside handle_user_message: {e}")
        return [("text", "Please try again later.")]