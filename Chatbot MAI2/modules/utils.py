LEVEL_TO_POINTS = [0, 50]  # to be filled


def level_to_points(level: int) -> int:
    global LEVEL_TO_POINTS
    if level < len(LEVEL_TO_POINTS):
        return LEVEL_TO_POINTS[level]
    # the magical formula!
    LEVEL_TO_POINTS.append(LEVEL_TO_POINTS[-1] + 50*len(LEVEL_TO_POINTS))
    return level_to_points(level)


def points_to_level(points: int) -> int:
    """ may return a too small level if it's not cached """
    for i, p in enumerate(LEVEL_TO_POINTS):
        if points < p:
            return i
    return len(LEVEL_TO_POINTS)


def try_fun(fun, default, *args, **kwargs):
    try:
        return fun(*args, **kwargs)
    except:
        return default
