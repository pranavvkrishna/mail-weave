import re
import spacy

# load spaCy's small English NLP model
nlp = spacy.load("en_core_web_sm")

# clock times: 6:30pm, 11:59 PM, 6pm, 6 p.m., 18:00, noon, midnight (any capitalization)
TIME_REGEX = re.compile(
    r'\b\d{1,2}(?::\d{2})?\s?(?:a\.m\.|p\.m\.|am|pm)(?!\w)'
    r'|\b(?:[01]?\d|2[0-3]):[0-5]\d\b'
    r'|\b(?:noon|midnight)\b',
    re.IGNORECASE,
)

# words that signal "this sentence is about a deadline"
STRONG_WORDS = ("due", "deadline", "submit", "submission", "turn in",
                "no later than", "closes", "expires", "last day")
WEAK_WORDS = ("by", "before", "until", "ends")


def _deadline_score(sentence: str) -> int:
    s = sentence.lower()
    score = 0
    for w in STRONG_WORDS:
        if re.search(rf'\b{re.escape(w)}\b', s):
            score += 2
    for w in WEAK_WORDS:
        if re.search(rf'\b{re.escape(w)}\b', s):
            score += 1
    return score


def _find_dates_and_times(text: str, sent):
    """Dates and times inside one sentence, as (start_char, text) pairs."""
    dates = [(e.start_char, e.text) for e in sent.ents if e.label_ == "DATE"]

    # regex matches are clean and exact, so they always run (not just as a fallback)
    regex_times = [(m.start(), m.group(0))
                   for m in TIME_REGEX.finditer(text, sent.start_char, sent.end_char)]

    # keep spaCy's TIME entities only when they don't overlap a regex match
    # (e.g. "tonight"); this also avoids spaCy entities that run into the next sentence
    times = list(regex_times)
    for e in sent.ents:
        if e.label_ != "TIME":
            continue
        overlaps = any(e.start_char < s + len(t) and s < e.end_char for s, t in regex_times)
        if not overlaps:
            times.append((e.start_char, e.text))

    return dates, sorted(times)


def extract_deadline(text: str):
    doc = nlp(text)

    best = None  # (score, -position, date_part, time_part)
    for i, sent in enumerate(doc.sents):
        dates, times = _find_dates_and_times(text, sent)
        if not dates and not times:
            continue
        score = _deadline_score(sent.text)
        # prefer the longest date; on a tie, the first one in the sentence
        date_part = max(dates, key=lambda d: len(d[1]))[1] if dates else None
        time_part = times[0][1] if times else None
        candidate = (score, -i, date_part, time_part)
        if best is None or candidate[:2] > best[:2]:
            best = candidate

    if best is None:
        return None
    _, _, date_part, time_part = best
    if date_part and time_part:
        return f"{date_part} at {time_part}"
    return date_part or time_part


def extract_all_deadlines(text: str):
    """Every date and time found in the whole text (useful for debugging)."""
    doc = nlp(text)
    all_dates, all_times = [], []
    for sent in doc.sents:
        d, t = _find_dates_and_times(text, sent)
        all_dates += [x[1] for x in d]
        all_times += [x[1] for x in t]
    return {"dates": all_dates, "times": all_times}


# quick manual test
if __name__ == "__main__":
    test_emails = [
        "CS161 Homework 3 due Friday at 11:59 PM",
        "Reminder: Assignment 3 due Wednesday at 6:30pm",
        "The final exam is scheduled for Tuesday, June 10 at 7:00pm",
        "Applications are due next month",
        "This is just a general announcement with no date",
        "Deadline extended to Monday, December 25th",
        # two events: the deadline is Friday 11:59pm, not Monday 2pm
        "Office hours are Monday at 2pm. The assignment is due Friday at 11:59pm.",
        "Assignment due Friday at 5 PM. Office hours are Monday at 2pm.",
        "Sale ends Friday",
    ]

    print("Testing deadline extraction:\n")
    for email in test_emails:
        print(f"Text: \"{email}\"")
        print(f"  Deadline:  {extract_deadline(email)}")
        print(f"  All found: {extract_all_deadlines(email)}")
        print()