

def remove_last_bracketed_string(track_name):
    # This will try to do a basic "parse" of the track name and remove anything
    # like [Explicit] or (Album Version)
    parsed_track_name = track_name
    if track_name.endswith("]"):
        start_idx = track_name.find("[")
        parsed_track_name = track_name[:start_idx - 1]
    elif track_name.endswith(")"):
        # Something to keep in mind here, you could have something like
        # "Forgotten (Lost Angels) (Album Version)", so you could end up
        # Removing more than you need
        start_idx = track_name.find("(")
        parsed_track_name = track_name[:start_idx - 1]
    return parsed_track_name


def remove_bracketed_strings_from_end(track_name):
    parsed_track_name = track_name
    for s,e in ("[", "]"), ("(", ")"):
        if parsed_track_name.endswith(e):
            start_idx = track_name.find(s)
            parsed_track_name = track_name[:start_idx - 1]
    return parsed_track_name



def remove_explicit_notation(track_name):
    parsed_track_name = track_name
    if "[Explicit" in track_name:
        start_idx = track_name.find("[Explicit")
        parsed_track_name = track_name[:start_idx - 1]
    return parsed_track_name


def remove_extra_notations(track_name):
    parsed_track_name = track_name
    for token in "[Explicit", "(Album":
        if token in parsed_track_name:
            start_idx = parsed_track_name.find(token)
            parsed_track_name = track_name[:start_idx - 1]
    return parsed_track_name


def get_default():
    return remove_bracketed_strings_from_end


def parse_using_default(track_name):
    return get_default()(track_name)
