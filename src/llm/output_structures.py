
import typing


class Event(typing.TypedDict):
    event_name: str
    event_description: str
    event_date: str
    event_time: str
    event_location: str
    sender: str



class CategorizedEvents(typing.TypedDict): # This is the output structure
    category: str
    event: Event

class SylabusEvents(typing.TypedDict):
    event_name: str
    course_code: str
    week_info: str
    category: str


class ListOfSylabusEvents(typing.TypedDict):
    events: list[SylabusEvents]

