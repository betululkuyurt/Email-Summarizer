

from datetime import datetime, timedelta
import re
from dateutil.parser import parse
from pytz import timezone, utc
import PyPDF2
from docx import Document



def display_events(events, filter_category=None):
    """
    Display events in a table format with optional filtering by category.
    
    :param events: List of categorized events
    :param filter_category: Optional category to filter events
    :return: HTML table of filtered events
    """
    import pandas as pd

    # Extract event details into separate columns
    formatted_events = []
    for event in events:
        event_details = event['event']
        event_details['category'] = event['category']
        formatted_events.append(event_details)

    # Convert events to DataFrame
    df = pd.DataFrame(formatted_events)

    # Apply filtering if a category is specified
    if filter_category and filter_category != 'All':
        df = df[df['category'] == filter_category]
    
    # If no events match the filter, return a message
    if df.empty:
        return "<p>No events found in the selected category.</p>"
    
    column_order = ['category', 'event_name', 'event_date', 'event_description', 'event_location', 'event_time']
    df = df[column_order]

    # Return the DataFrame as HTML
    return df.to_html(index=True)




def get_unique_categories(events):
    """
    Extract unique categories from the events list.
    
    :param events: List of categorized events
    :return: List of unique categories
    """
    categories = set(['All'])  # Include 'All' as a default option
    for event in events:
        # Safely get the 'category' key with a default value
        category = event.get('category', None)
        if category:
            categories.add(category)
        else:
            print(f"Warning: Missing 'category' key in event: {event}")
    return list(categories)




def normalize_datetime(event_date, event_time=None):
    """
    Normalize event date and time, handle 'Not Specified' cases and unexpected input formats.
    If no event_time is specified but event_date exists, default to 12:00 PM.
    If both event_date and event_time are missing, return None.
    """
    try:
        # Handle unspecified date
        if not event_date or event_date.lower() == "not specified":
            print(f"Skipping event with unspecified date: {event_date}")
            return None

        # If no event_time is provided, set it to 12:00 PM if event_date is present
        if not event_time or event_time.lower() == "not specified":
            event_time = "12:00"
            print(f"Setting default time to: {event_time}")

        # Handle single-day or multi-day date ranges
        if "-" in event_date or "–" in event_date:
            try:
                start_date_str, end_date_str = map(str.strip, re.split(r"[-–]", event_date))
                start_date = parse(start_date_str, dayfirst=True)
                end_date = parse(end_date_str, dayfirst=True)
            except Exception as e:
                print(f"Failed to parse date range: {event_date}. Error: {e}")
                return None
        else:
            try:
                start_date = parse(event_date, dayfirst=True)
                end_date = start_date
            except Exception as e:
                print(f"Failed to parse single date: {event_date}. Error: {e}")
                return None

        # Clean up and parse time ranges
        event_time = event_time.replace(".", ":")
        if "-" in event_time or "–" in event_time:
            try:
                start_time, end_time = map(str.strip, re.split(r"[-–]", event_time))
                start_time = parse(start_time).time()
                end_time = parse(end_time).time()
            except Exception as e:
                print(f"Failed to parse time range: {event_time}. Error: {e}")
                return None
        else:
            try:
                start_time = parse(event_time).time()
                end_time = (datetime.combine(datetime.min, start_time) + timedelta(hours=1)).time()  # Default 1-hour duration
            except Exception as e:
                print(f"Failed to parse single time: {event_time}. Error: {e}")
                return None

        # Convert to UTC with timezone adjustments
        local_tz = timezone("Europe/Istanbul")
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            try:
                start_dt = local_tz.localize(datetime.combine(current_date, start_time))
                end_dt = local_tz.localize(datetime.combine(current_date, end_time))
                date_range.append({
                    "start": start_dt.astimezone(utc).isoformat(),
                    "end": end_dt.astimezone(utc).isoformat(),
                    "is_all_day": False,
                })
            except Exception as e:
                print(f"Failed to create datetime object for date: {current_date}. Error: {e}")
                return None
            current_date += timedelta(days=1)

        return date_range

    except Exception as e:
        print(f"General error in normalize_datetime: {e}")
        return None



def extract_text_from_file(file_path):
    """
    Extract text from Word or PDF file.
    """
    text = ""
    if file_path.endswith(".docx"):
        # Extract text from Word file
        document = Document(file_path)
        for para in document.paragraphs:
            text += para.text + "\n"
    elif file_path.endswith(".pdf"):
        # Extract text from PDF file
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    else:
        return "Unsupported file format."
    return text