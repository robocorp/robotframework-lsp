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
    instance.clear_cache(instance)

    """
    cache_name = "__cache__%s" % (func.__name__,)

    @functools.wraps(func)
    def new_func(self, *args, **kwargs):
        try:
            return getattr(self, cache_name)
        except AttributeError:
            ret = func(self, *args, **kwargs)
            setattr(self, cache_name, ret)
            return ret

    def clear_cache(self):
        try:
            delattr(self, cache_name)
        except AttributeError:
            pass

    new_func.clear_cache = clear_cache
    return new_func
