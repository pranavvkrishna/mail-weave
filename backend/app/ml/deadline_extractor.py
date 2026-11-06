import re
from datetime import datetime
import dateparser
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

# dates that spaCy often misses or cuts short. Matches things like:
# 11/12   11/12/2026   Oct 23   October 23rd, 2026   23rd Oct   23 October
# Friday, Oct 23   next Friday 23rd Oct   Fri Oct 23

_MONTH = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
_WEEKDAY = r'(?:mon(?:day)?|tues?(?:day)?|wed(?:nesday)?|thu(?:rs?)?(?:day)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)'
_DAYNUM = r'\d{1,2}(?:st|nd|rd|th)?'

DATE_REGEX = re.compile(
    rf'\b(?:(?:(?:next|this)\s+)?{_WEEKDAY}\.?,?\s+)?'
    rf'(?:{_MONTH}\.?\s+{_DAYNUM}|{_DAYNUM}\s+(?:of\s+)?{_MONTH}\b\.?)(?:,?\s+\d{{4}})?'
    r'|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b',
    re.IGNORECASE,
)

# spaCy also tags lengths of time as DATE ("1 day", "the full day", "2 weeks")
#  those are not deadlines, so we throw them away.
DURATION_REGEX = re.compile(
    r'^(?:(?:the|a|an|one|\d+|few|couple of)\s+)?(?:(?:full|whole|entire)\s+)?'
    r'(?:day|days|week|weeks|month|months|year|years|weekend|weekends)(?:\s+(?:out|ago|left))?$',
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


def _segments(doc):
    # sentences as (start_char, end_char).
    # spaCy sometimes cuts a sentence in the middle ("next Friday 23rd | Oct at 5pm."),
    # so we glue its pieces together until one really ends with . ! ? and then we also
    # cut at every line break (a new line is a new thought in an email)

    text = doc.text
    glued, seg_start = [], None
    for sent in doc.sents:
        if seg_start is None:
            seg_start = sent.start_char
        if sent.text.rstrip().endswith((".", "!", "?")):
            glued.append((seg_start, sent.end_char))
            seg_start = None
    if seg_start is not None:
        glued.append((seg_start, len(text)))

    segs = []
    for s, e in glued:
        pos = s
        for line in text[s:e].split("\n"):
            if line.strip():
                segs.append((pos, pos + len(line)))
            pos += len(line) + 1
    return segs


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def _find_dates_and_times(text: str, doc, start: int, end: int):
    # Dates and times inside one segment of text, as (start_char, text) pairs
    ents = [e for e in doc.ents if e.start_char >= start and e.end_char <= end]
    dates = [(e.start_char, e.text) for e in ents if e.label_ == "DATE" and not DURATION_REGEX.match(e.text.strip())]

    # regex dates: when one overlaps a spaCy date, keep whichever is longer
    for m in DATE_REGEX.finditer(text, start, end):
        m_start, m_end = m.start(), m.end()
        clash = [(s, t) for s, t in dates if _overlaps(s, s + len(t), m_start, m_end)]
        if all(len(t) < len(m.group(0)) for _, t in clash):
            dates = [d for d in dates if d not in clash]
            dates.append((m_start, m.group(0)))

    # regex matches are clean and exact, so they always run (not just as a fallback)
    regex_times = [(m.start(), m.group(0)) for m in TIME_REGEX.finditer(text, start, end)]

    # keep spaCy's TIME entities only when they don't overlap a regex match
    # (e.g. "tonight"); this also avoids spaCy entities that run into the next sentence
    times = list(regex_times)
    for e in ents:
        if e.label_ != "TIME":
            continue
        # spaCy also tags junk like "hours" or "a week" as TIME: keep real clock words only
        if not re.search(r'\d|tonight|morning|afternoon|evening|noon|midnight', e.text, re.IGNORECASE):
            continue
        if not any(_overlaps(e.start_char, e.end_char, s, s + len(t)) for s, t in regex_times):
            times.append((e.start_char, e.text))

    return dates, sorted(times)


def extract_deadline(text: str):
    doc = nlp(text)

    best = None  # (score, -position, date_part, time_part)
    for i, (start, end) in enumerate(_segments(doc)):
        dates, times = _find_dates_and_times(text, doc, start, end)
        if not dates and not times:
            continue
        score = _deadline_score(text[start:end])
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


def _parse_sent_date(sent_date: str | None) -> datetime:
    # email's own date (from Gmail), or right now if it can't be read
    if sent_date:
        parsed = dateparser.parse(sent_date)
        if parsed:
            return parsed.replace(tzinfo=None)
    return datetime.now()


def resolve_deadline(deadline_text: str | None, sent_date: str | None = None):
    # turn text like 'Friday at 11:59pm' into a real date.
    # weekday names are counted forward from the day the email was SENT, so
    # 'Friday' in an email sent on Wednesday Nov 4 becomes Friday Nov 6.
    # Returns {"iso": ..., "display": ...} or None if it can't be understood.

    if not deadline_text:
        return None

    text = deadline_text

    # too vague to turn into one day ("next month", "this week")
    if re.search(r'\b(?:next|this|last)\s+(?:week|month|year)\b', text, re.IGNORECASE):
        return None

    # "tonight" means end of day
    text = re.sub(r'(?:\bat\s+)?\btonight\b', 'at 11:59pm', text, flags=re.IGNORECASE)

    # "Friday, Oct 23" / "next Friday 23rd Oct": trust the calendar date and drop the
    # weekday (it can disagree with the date, and "next" would shift the day)
    if re.search(rf'{_MONTH}\.?\s+\d|\d(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}', text, re.IGNORECASE):
        text = re.sub(rf'\b(?:(?:next|this)\s+)?{_WEEKDAY}\b\.?,?\s*', '', text, flags=re.IGNORECASE)

    base = _parse_sent_date(sent_date)
    parsed = dateparser.parse(
        text,
        settings={
            "RELATIVE_BASE": base,
            "PREFER_DATES_FROM": "future",
            "DATE_ORDER": "MDY",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    if parsed is None:
        return None

    has_time = bool(TIME_REGEX.search(text))
    if has_time:
        iso = parsed.strftime("%Y-%m-%dT%H:%M")
        display = parsed.strftime("%a, %b %-d, %-I:%M %p")
    else:
        iso = parsed.strftime("%Y-%m-%d")
        display = parsed.strftime("%a, %b %-d")
    return {"iso": iso, "display": display}


def extract_all_deadlines(text: str):
    # every date and time found in the whole text
    doc = nlp(text)
    all_dates, all_times = [], []
    for start, end in _segments(doc):
        d, t = _find_dates_and_times(text, doc, start, end)
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
        # an explicit date next to the weekday
        "The assignment is due next Friday 23rd Oct at 5pm.",
        "Due Fri Oct 23 at 11:59pm",
        "Please submit by 11/12.",
    ]

    print("Testing deadline extraction:\n")
    for email in test_emails:
        print(f"Text: \"{email}\"")
        found = extract_deadline(email)
        print(f"  Deadline:  {found}")
        print(f"  Resolved:  {resolve_deadline(found, 'Fri, Oct 16, 2026, 9:00 AM')}")
        print(f"  All found: {extract_all_deadlines(email)}")
        print()