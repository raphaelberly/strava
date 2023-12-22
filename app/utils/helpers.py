def format_timedelta(s):
    s = s.dt.total_seconds()

    seconds = (s % 60).astype(int).astype(str).str.zfill(2)
    minutes = (s // 60 % 60).astype(int).astype(str).str.zfill(2)
    hours = (s // 3600).astype(int).astype(str)

    return hours + ':' + minutes + ':' + seconds
