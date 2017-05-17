MSG_INIT_SUCCESSFUL = 'This thread is now an RSVPBot event for **[{}]({})**! Type `rsvp help` for more options.'
MSG_DATE_SET = 'The date for **%s** has been set to **%s**!\n`rsvp help` for more options.'
MSG_TIME_SET = 'The time for **%s** has been set to **%02d:%02d**!.\n`rsvp help` for more options.'
MSG_DURATION_SET = 'The duration for **%s** has been set to **%s**!.\n`rsvp help` for more options.'
MSG_TIME_SET_ALLDAY = '**%s** is now an all day long event.'
MSG_STRING_ATTR_SET = "The %s for this event has been set to **%s**!\n`rsvp help` for more options."
MSG_ATTENDANCE_LIMIT_SET = "The attendance limit for this event has been set to **%d**! Hurry up and `rsvpyes` now!.\n`rsvp help` for more options"
MSG_EVENT_CANCELED = "The event has been canceled!"
MSG_EVENT_MOVED = "This event has been moved to **[%s](%s)**!"
MSG_ADDED_TO_CALENDAR = "Event [added to {calendar_name} Calendar]({url})!"
ERROR_INVALID_COMMAND = "`%s` is not a valid RSVPBot command! Type `rsvp help` for the correct syntax."
ERROR_NOT_AN_EVENT = "This thread is not an RSVPBot event!. Type `rsvp init` to make it into an event."
ERROR_NOT_AUTHORIZED_TO_DELETE = "Oops! You cannot cancel this event! Only the event's original creator can do so."
ERROR_ALREADY_AN_EVENT = "Oops! That thread is already an RSVPBot event!"
ERROR_TIME_NOT_VALID = "Oops! **%02d:%02d** is not a valid time!"
ERROR_DATE_NOT_VALID = "Oops! **%s** is not a valid date in the **future**!"
ERROR_LIMIT_REACHED = "Oh no! The **limit** for this event has been reached!"
ERROR_MISSING_MOVE_DESTINATION = "`rsvp move` requires a Zulip stream URL destination (e.g. 'https://recurse.zulipchat.com/#narrow/stream/announce/topic/All.20Hands.20Meeting')"
ERROR_BAD_MOVE_DESTINATION = "%s is not a valid move destination URL! `rsvp move` requires a Zulip stream URL destination (e.g. 'https://recurse.zulipchat.com/#narrow/stream/announce/topic/All.20Hands.20Meeting') Type `rsvp help` for the correct syntax."
ERROR_MOVE_ALREADY_AN_EVENT = "Oops! %s is already an RSVPBot event!"
ERROR_CALENDAR_ENVS_NOT_SET = 'Oops! Adding to Calendar not currently supported.'
ERROR_DATE_AND_TIME_NOT_SET = 'Oops! The `date` and `time` are required to add this to the calendar!'
ERROR_DURATION_NOT_SET = 'Oops! The event `duration` is required to add this to the calendar!'



ANNOUNCE_MESSAGE = """
**[{title}]({url})**
{timestamp}
Created by {created_by}

To start an RSVPBot thread for this event:
```rsvp init {url}```
""".strip()

ERROR_NO_EVENT_ID = """
`rsvp init` must be passed an RC Calendar event ID or URL. For example:

```
rsvp init https://www.recurse.com/calendar/123-my-event
```
""".strip()

ERROR_EVENT_NOT_FOUND = "Oops! I couldn't find this event: {}"
ERROR_EVENT_ALREADY_INITIALIZED = "Oops! This event was already initialized here: {}"
ERROR_GOOGLE_CALENDAR_NO_LONGER_USED = "Oops! RSVPBot no longer uses Google Calendar, but it uses the [RC Calendar](https://www.recurse.com/calendar) instead. This event can be found [here]({})."
ERROR_FUNCTIONALITY_MOVED = "Oops! RSVPBot doesn't support `rsvp {}` directly anymore. You can now do this [on the RC calendar]({})!"
ERROR_RSVP_MAYBE_NOT_SUPPORTED = "Oops! `rsvp maybe` is no longer supported."
ERROR_CANNOT_INIT_IN_ANNOUNCE_THREAD = "Oops! You cannot `rsvp init` in the announce thread."
