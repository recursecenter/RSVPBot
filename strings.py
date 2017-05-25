import config

ANNOUNCE_MESSAGE = """
**[{title}]({url})**
{timestamp}
Created by {created_by}

To start an RSVPBot thread for this event:
```{key_word} init {url}```
""".strip()

MSG_CREATE_EVENT_ON_RC_CALENDAR = """
RSVPBot events are saved on the RC calendar. To create an event that will be tracked in this thread, go here: %s/calendar/new?{}
""".strip() % config.rc_root

MSG_INIT_SUCCESSFUL = 'This thread is now an RSVPBot event for **[{}]({})**! Type `rsvp help` for more options.'
MSG_EVENT_MOVED = "This event has been moved to **[%s](%s)**!"

ERROR_INVALID_COMMAND = "`%s` is not a valid RSVPBot command! Type `rsvp help` for the correct syntax."
ERROR_NOT_AN_EVENT = "This thread is not an RSVPBot event! Type `rsvp init event-url` to make it into an event."
ERROR_ALREADY_AN_EVENT = "Oops! That thread is already an RSVPBot event!"
ERROR_MISSING_MOVE_DESTINATION = "`rsvp move` requires a Zulip stream URL destination (e.g. 'https://recurse.zulipchat.com/#narrow/stream/announce/topic/All.20Hands.20Meeting')"
ERROR_BAD_MOVE_DESTINATION = "%s is not a valid move destination URL! `rsvp move` requires a Zulip stream URL destination (e.g. 'https://recurse.zulipchat.com/#narrow/stream/announce/topic/All.20Hands.20Meeting') Type `rsvp help` for the correct syntax."
ERROR_MOVE_ALREADY_AN_EVENT = "Oops! %s is already an RSVPBot event!"
ERROR_EVENT_NOT_FOUND = "Oops! I couldn't find this event: {}"
ERROR_EVENT_ALREADY_INITIALIZED = "Oops! This event was already initialized here: {}"
ERROR_GOOGLE_CALENDAR_NO_LONGER_USED = "Oops! RSVPBot no longer uses Google Calendar, but it uses the [RC Calendar](%s/calendar) instead. This event can be found [here]({})." % config.rc_root
ERROR_FUNCTIONALITY_MOVED = "Oops! RSVPBot doesn't support `rsvp {}` directly anymore. You can now do this [on the RC calendar]({})!"
ERROR_RSVP_MAYBE_NOT_SUPPORTED = "Oops! `rsvp maybe` is no longer supported."
ERROR_CANNOT_INIT_IN_ANNOUNCE_THREAD = "Oops! You cannot `rsvp init` in the announce thread."
ERROR_SERVER_EXCEPTION = ":scream: Something went terribly wrong inside RSVPBot. If this keeps happening, please ping `@Faculty`!"

ERROR_NO_EVENT_ID = """
`rsvp init` must be passed an RC Calendar event ID or URL. For example:

```
rsvp init %s/calendar/123-my-event
```
""".strip() % config.rc_root

ERROR_THREAD_FROM_RC_ALREADY_AN_EVENT = """
Oops! Someone tried to create an event on the RC calendar using this thread, but it's already tracking an event.

Here's the event: **[{title}]({url})**

To start another RSVPBot thread for this event:
```rsvp init {url}```
""".strip()
