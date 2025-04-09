# Configuration
import requests

from src.util.display_helpers import normalize_datetime


TENANT_ID = 'organizations'
CLIENT_ID = '687ec9a1-ccad-4541-8c9e-2e081c62cfea'
DENIZ_CLIENT_ID =  '1877c3a9-d260-4a04-a5ba-d98aa85a0d96'
Betul_CLIENT_ID = '18329ed6-bbf6-4962-8503-0cf9a75d72af'
SCOPES = "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Calendars.ReadWrite"
TOKEN_URL = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'


def get_access_token(username, password):
    """Obtain an access token using username and password."""
    data = {
        'grant_type': 'password',
        'client_id': Betul_CLIENT_ID,
        'scope': SCOPES,
        'username': username,
        'password': password
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(TOKEN_URL, data=data, headers=headers)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        raise Exception(f"Failed to obtain token: {response.text}")

def fetch_inbox(token, mail_count):
    """Fetch the user's inbox messages using Graph API with a specified limit."""
    url = f'https://graph.microsoft.com/v1.0/me/messages?$top={mail_count}'
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        messages = response.json().get('value', [])
        return [
            {
                "from": msg.get("from", {}).get("emailAddress", {}).get("address", "Unknown Sender"),
                "receivedDateTime": msg.get("receivedDateTime", "Unknown Time"),
                "subject": msg.get("subject", "No Subject"),
                "body": msg.get("body", {}).get("content", "No Content")
            }
            for msg in messages
        ]
    else:
        raise Exception(f"Failed to fetch inbox: {response.text}")


def authenticate(username, password):
    """Authenticate the user using their username and password, and confirm access to profile and calendar."""
    try:
        # Step 1: Get the access token
        token = get_access_token(username, password)
        headers = {'Authorization': f'Bearer {token}'}

        # Step 2: Fetch the user's profile
        profile_response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
        if profile_response.status_code == 200:
            user = profile_response.json()
            profile_message = f"Authentication successful!\nWelcome, {user['displayName']} ({user['userPrincipalName']})"
        else:
            return f"Authentication failed during profile retrieval: {profile_response.text}"

        # Step 3: Fetch the user's calendar events to confirm access
        events_response = requests.get('https://graph.microsoft.com/v1.0/me/events', headers=headers)
        if events_response.status_code == 200:
            calendar_message = "Authentication successful for accessing the calendar."
        else:
            return f"Authentication failed during calendar access: {events_response.text}"

        # Combine the profile and calendar access messages
        return profile_message + "\n" + calendar_message

    except Exception as e:
        return f"Authentication failed: {str(e)}"
 


def add_events_to_calendar(filtered_events, username, password):
    """
    Add filtered events to the user's Outlook calendar and display added events.
    """
    try:
        # Authenticate and get the token
        token = get_access_token(username, password)

        if not filtered_events:
            return "<p>No filtered events to add.</p>"

        added_events = []  # List to collect successfully added events

        # Loop through filtered events and add them to the calendar
        for event in filtered_events:
            # Ensure event data exists and is structured correctly
            event_details = event.get('event', {})
            if not event_details:
                print(f"Skipping event due to missing details: {event}")
                continue

            # Extract event details
            subject = event_details.get('event_name', 'No Subject')
            body = event_details.get('event_description', 'No Description')
            event_date = event_details.get('event_date', '')
            raw_time = event_details.get('event_time', '')
            location = event_details.get('event_location', 'Online')

            # Parse the time
            datetime_info = normalize_datetime(event_date, raw_time)
            if not datetime_info:
                print(f"Skipping event due to date/time parsing failure: {subject}")
                continue

            # Create a calendar event for each day in the date range
            for date_info in datetime_info:
                event_payload = {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": body,
                    },
                    "location": {
                        "displayName": location,
                    },
                    "start": {
                        "dateTime": date_info["start"],
                        "timeZone": "UTC",
                    },
                    "end": {
                        "dateTime": date_info["end"],
                        "timeZone": "UTC",
                    },
                }

                # Make the API call to add the event
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                response = requests.post(
                    'https://graph.microsoft.com/v1.0/me/events',
                    headers=headers,
                    json=event_payload,
                )

                if response.status_code == 201:
                    added_events.append({
                        "event_name": subject,
                        "event_date": event_date,
                        "event_time": raw_time,
                        "location": location,
                    })
                else:
                    print(f"Failed to add event '{subject}': {response.text}")

        # Format added events for display
        if added_events:
            return (
                "<p>Successfully added events to the calendar:</p>" +
                "<ul>" +
                "".join([f"<li>{event['event_name']} - {event['event_date']} {event['event_time']} at {event['location']}</li>" for event in added_events]) +
                "</ul>"
            )
        else:
            return "<p>No events were successfully added to the calendar.</p>"

    except Exception as e:
        return f"<p>Error while adding events: {str(e)}</p>"