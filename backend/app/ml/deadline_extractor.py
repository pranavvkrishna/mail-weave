import re
import spacy

# load spaCy's small English NLP model
nlp = spacy.load("en_core_web_sm")

# regex fallback for compact time formats spaCy sometimes misses (like "6:30pm")
TIME_REGEX = re.compile(r'\b\d{1,2}:\d{2}\s?(?:am|pm|AM|PM)\b')


def extract_time_fallback(text: str):
    # regex if spaCy can't find time
    match = TIME_REGEX.search(text)
    return match.group(0) if match else None


def extract_deadline(text: str):
    doc = nlp(text)

    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    times = [ent.text for ent in doc.ents if ent.label_ == "TIME"]

    # prefer the longest date match (most complete/specific one)
    date_part = max(dates, key=len) if dates else None
    time_part = times[0] if times else extract_time_fallback(text)

    if date_part and time_part:
        return f"{date_part} at {time_part}"
    elif date_part:
        return date_part
    elif time_part:
        return time_part
    return None


def extract_all_deadlines(text: str):
    doc = nlp(text)
    dates = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    times = [ent.text for ent in doc.ents if ent.label_ == "TIME"]

    # use regex fallback if spaCy found no times
    if not times:
        fallback = extract_time_fallback(text)
        if fallback:
            times = [fallback]

    return {"dates": dates, "times": times}


# quick manual test
if __name__ == "__main__":
    test_emails = [
        "CS161 Homework 3 due Friday at 11:59 PM",
        "Reminder: Assignment 3 due Wednesday at 6:30pm",
        "The final exam is scheduled for Tuesday, June 10 at 7:00pm",
        "Applications are due next month",
        "This is just a general announcement with no date",
        "Deadline extended to Monday, December 25th",
    ]

    print("Testing deadline extraction:\n")
    for email in test_emails:
        deadline = extract_deadline(email)
        all_found = extract_all_deadlines(email)
        print(f"Text: \"{email}\"")
        print(f"  Combined deadline: {deadline}")
        print(f"  All dates found:   {all_found['dates']}")
        print(f"  All times found:   {all_found['times']}")
        print()