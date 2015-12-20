def cap_list_to_dict(l):
    d = {}
    for cap in l:
        if '=' in cap:
            (key, value) = cap.split('=', 1)
        else:
            key = cap
            value = None
        d[key] = value
    return d
