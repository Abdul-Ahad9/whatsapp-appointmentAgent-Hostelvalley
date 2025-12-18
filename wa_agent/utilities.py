import httpx
import json
import os
from dotenv import load_dotenv
import openai

import google.generativeai as genai

load_dotenv()

client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
MY_API_URL = os.getenv("MY_API_URL", "https://api.example.com/data")

# --- Helper: Send WhatsApp Message ---
# async def send_whatsapp_message(to: str, message: str):
#     try:
#         url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
#         headers = {
#             "Authorization": f"Bearer {WHATSAPP_TOKEN}",
#             "Content-Type": "application/json"
#         }
#         payload = {
#             "messaging_product": "whatsapp",
#             "to": to,
#             "type": "text",
#             "text": {"body": message}
#         }
#         print(f"Sending message to {to}: {message}")
#         print(f"Payload: {json.dumps(payload, indent=2)}")
#         print(f"Headers: {json.dumps(headers, indent=2)}")
#         async with httpx.AsyncClient() as client:
#             r = await client.post(url, headers=headers, json=payload)
#             print(f"Response: {r.status_code} - {r.text}")
#         if r.status_code != 200:
#             print(f"Failed to send message: {r.text}")
#             return r.status_code == 200
#         print(f"WhatsApp message sent successfully to {to}")
#     except Exception as e:
#         print(f"Error sending WhatsApp message: {e}")
#         return False
    

# def send_whatsapp_image(to, image_url, caption):
#     headers = {
#         "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "messaging_product": "whatsapp",
#         "to": to,
#         "type": "image",
#         "image": {
#             "link": image_url,
#             "caption": caption
#         }
#     }

#     res = requests.post(
#         f"https://graph.facebook.com/v19.0/{os.getenv('PHONE_NUMBER_ID')}/messages",
#         headers=headers,
#         json=payload
#     )

#     return res.json()

# for hostel in hostels[:3]:
#     send_whatsapp_image(sender_id, hostel["image_url"], f"{hostel['name']} - {hostel.get('price')}")


# whatsapp_sender.py
import os
import aiohttp

PHONE_ID = os.getenv("PHONE_NUMBER_ID")
WA_TOKEN = os.getenv("WHATSAPP_TOKEN")
WA_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

headers = {
    "Authorization": f"Bearer {WA_TOKEN}",
    "Content-Type": "application/json"
}

async def send_whatsapp_message(phone: str, message_type: str, content: str, caption: str = ""):
    try:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone
        }

        if message_type == "text":
            payload["type"] = "text"
            payload["text"] = {"body": content}
        elif message_type == "image":
            payload["type"] = "image"
            payload["image"] = {"link": content, "caption": caption}

        # async with aiohttp.ClientSession() as session:
        #     async with session.post(WA_URL, headers=headers, json=payload) as resp:
        #         if resp.status != 200:
        #             print(f"Failed to send message: {await resp.text()}")
        async with httpx.AsyncClient() as client:
            r = await client.post(WA_URL, headers=headers, json=payload)
            print(f"Response: {r.status_code} - {r.text}")
        if r.status_code != 200:
            print(f"Failed to send message: {r.text}")
            return r.status_code == 200
        print(f"WhatsApp message sent successfully to {phone}")
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")


    

# # --- Helper: Extract Location & City using GPT ---
# def extract_location_and_city(message_text: str):
#     prompt = (
#         "Extract the 'location' and 'city' from the following message. "
#         "If either is missing, return null for it. Respond in JSON like: "
#         '{"city": "CityName", "location": "LocationName"}\n\n'
#         f"Message: {message_text}"
#     )
#     response = client.chat.completion.create(
#         model="gpt-4",
#         messages=[{"role": "user", "content": prompt}]
#     )
#     content = response.choices[0].message["content"]

#     try:
#         data = json.loads(content)
#         return data.get("city"), data.get("location")
#     except Exception as e:
#         print(f"OpenAI JSON parse error: {e}")
#         return None, None
    

# # --- Helper: Extract Location & City using GPT ---
# def extract_location_and_city(message_text: str, client: openai.OpenAI):
#     prompt = (
#         "Extract the 'location' and 'city' from the following message. "
#         "If either is missing, return null for it. Respond in JSON like: "
#         '{"city": "CityName", "location": "LocationName"}\n\n'
#         f"Message: {message_text}"
#     )

#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o", 
#             response_format="json",
#             messages=[{"role": "user", "content": prompt}]
#         )
        
#         # Access the content attribute correctly
#         content = response.choices[0].message.content
#         print(f"GPT response content: {content}")
#         data = json.loads(content)
        
#         return data.get("city"), data.get("location")
    
#     except openai.APIError as e:
#         print(f"OpenAI API error: {e}")
#         return None, None
#     except json.JSONDecodeError as e:
#         print(f"JSON parse error: {e}")
#         return None, None
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#         return None, None


# --- Helper: Extract Location & City using Gemini ---
def extract_location_and_city(message_text: str):
    prompt = (
        "Extract the 'location' and 'city' from the following message. "
        "If either is missing, return null for it. Respond in JSON like: "
        '{"city": "CityName", "location": "LocationName"}\n\n'
        f"Message: {message_text}"
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        # Sometimes Gemini wraps the JSON in Markdown-style code block, strip if needed
        content = response.text.strip().strip("```json").strip("```").strip()
        print(f"Gemini response content: {content}")

        data = json.loads(content)
        return data.get("city"), data.get("location")

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None



# --- Helper: Call Your Custom API ---
async def fetch_data_from_api(city: str, location: str):
    params = {"city": city, "nearby": location}
    print(f"Fetching data from API with params: {params}")
    async with httpx.AsyncClient() as client:
        print(f"Calling API at {MY_API_URL} with params: {params}")
        r = await client.get(MY_API_URL, params=params)
        print(f"API response status: {r.status_code}")
        print(f"API response text: {r.text}")
        if r.status_code == 200:
            print(f"API response: {r.text}")
            return r.json()
    return None