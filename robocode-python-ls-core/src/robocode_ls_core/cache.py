import functools


def instance_cache(func):
    """
    Use as decorator:
    
    class MyClass(object):

        @instance_cache
        def cache_this(self):
            ...
            
    Clear the cache with:
    
    instance = MyClass()
    instance.cache_this()
    instance.cache_clear(instance)

    """
    cache_key = "__cache__%s" % (func.__name__,)

    @functools.wraps(func)
    def new_func(self, *args, **kwargs):
        try:
            cache = getattr(self, "__instance_cache__")
        except:
            cache = {}
            setattr(self, "__instance_cache__", cache)

        try:
            func_cache = cache[cache_key]
        except KeyError:
            func_cache = cache[cache_key] = {}

        args_cache_key = None
        if args:
            args_cache_key = (args_cache_key, tuple(args))
        if kwargs:
            # We don't do that because if the caller uses args and then
            # later kwargs, we'd have to match the parameter to the position,
            # so, simplify for now and don't accept kwargs.
            raise AssertionError("Cannot currently deal with kwargs.")

        try:
            return func_cache[args_cache_key]
        except KeyError:
            ret = func(self, *args, **kwargs)
            func_cache[args_cache_key] = ret
            return ret

    def cache_clear(self):
        try:
            cache = getattr(self, "__instance_cache__")
        except:
            pass
        else:
            cache.pop(cache_key, None)

    new_func.cache_clear = cache_clear
    return new_func
