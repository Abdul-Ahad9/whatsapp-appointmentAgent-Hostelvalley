from redis_client import get_session, set_session

def handle_user_message(user_message: str, sender_id: str):
    session = get_session(sender_id)

    # If in booking mode, collect next info
    if session.get("booking_step"):
        step = session["booking_step"]

        if step == "hostel_selected":
            session["hostel"] = user_message
            session["booking_step"] = "ask_date"
            set_session(sender_id, session)
            return "Great! When would you like to check in? (e.g. 25 August)"

        elif step == "ask_date":
            session["checkin_date"] = user_message
            session["booking_step"] = "ask_name"
            set_session(sender_id, session)
            return "Got it. Can I have your full name?"

        elif step == "ask_name":
            session["name"] = user_message
            session["booking_step"] = "ask_phone"
            set_session(sender_id, session)
            return "Thanks. Finally, your phone number please?"

        elif step == "ask_phone":
            session["phone"] = user_message
            session["booking_step"] = None  # Booking complete
            # Save to DB or send to admin here
            set_session(sender_id, {})  # Clear session

            return (
                f"✅ Booking request for *{session['hostel']}* on *{session['checkin_date']}* confirmed!\n"
                f"We’ll reach out to {session['phone']} if needed.\nThank you, {session['name']}!"
            )

    # Otherwise, parse intent using Gemini (as before)
    # ...

    # Example trigger: user says "I want to book XYZ Hostel"
    if "book" in user_message.lower():
        session["booking_step"] = "hostel_selected"
        set_session(sender_id, session)
        return "Sure! Which hostel would you like to book?"

    # continue regular handling...
