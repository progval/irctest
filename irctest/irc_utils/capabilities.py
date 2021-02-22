def cap_list_to_dict(caps):
    d = {}
    for cap in caps:
        if "=" in cap:
            (key, value) = cap.split("=", 1)
        else:
            key = cap
            value = None
        d[key] = value
    return d
