

def try_fun(fun, default, *args, **kwargs):
    try:
        return fun(*args, **kwargs)
    except:
        return default
