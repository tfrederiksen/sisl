# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from functools import reduce, update_wrapper
from itertools import zip_longest
from numbers import Integral
from textwrap import dedent
from typing import Any, Callable, Optional, Type

Func = Callable[..., Optional[Any]]


def postprocess_tuple(*funcs):
    """Post-processes the returned value according to the funcs for multiple data

    The internal algorithm will use zip_longest to apply the *last* `funcs[-1]` to
    the remaining return functions. Useful if there are many tuples that can
    be handled equivalently:

    Examples
    --------
    >>> postprocess_tuple(np.array) == postprocess_tuple(np.array, np.array)
    """

    def post(ret):
        nonlocal funcs
        if isinstance(ret[0], tuple):
            return tuple(
                func(r)
                for r, func in zip_longest(zip(*ret), funcs, fillvalue=funcs[-1])
            )
        return funcs[0](ret)

    return post


def is_sliceable(method: Func):
    """Check whether a function is implemented with the `SileBinder` decorator"""
    return isinstance(method, (SileBinder, SileBound))


class SileSlicer:
    """Handling io-methods in sliced behaviour for multiple returns

    This class handler can expose a slicing behavior of the function
    that it applies to.

    The idea is to attach a function/method to this class and
    let this perform the function at hand for slicing behaviour
    etc.
    """

    def __init__(
        self,
        obj: Type[Any],
        func: Func,
        key: Type[Any],
        *,
        skip_func: Optional[Func] = None,
        postprocess: Optional[Callable[..., Any]] = None,
    ):
        # this makes it work like a function bound to an instance (func._obj
        # works for instances)
        self._obj = obj
        # this is already sliced, sub-slicing shouldn't work (at least for now)
        update_wrapper(self, func)
        self.key = key
        if skip_func is None:
            self.skip_func = func
        else:
            self.skip_func = skip_func
        if postprocess is None:

            def postprocess(ret):
                return ret

        self.postprocess = postprocess

    def __call__(self, *args, **kwargs):
        """Defer call to the function"""
        # Now handle the arguments
        obj = self._obj
        func = self.__wrapped__
        key = self.key
        skip_func = self.skip_func

        # quick return if no slicing
        if key is None:
            return func(obj, *args, **kwargs)

        inf = 100000000000000

        def check_none(r):
            if isinstance(r, tuple):
                return reduce(lambda x, y: x and y is None, r, True)
            return r is None

        # Determine whether we can reduce the call overheads
        start = 0
        stop = inf

        if isinstance(key, Integral):
            if key >= 0:
                start = key
                stop = key + 1
        elif key.step is None or key.step > 0:  # step size of 1
            if key.start is not None:
                start = key.start
            if key.stop is not None:
                stop = key.stop
        elif key.step < 0:
            if key.stop is not None:
                start = key.stop
            if key.start is not None:
                stop = key.start

        if start < 0:
            start = 0
        if stop < 0:
            stop = inf
        assert stop >= start

        # collect returning values
        retvals = [None] * start
        append = retvals.append
        with obj:  # open sile
            # quick-skip using the skip-function
            for _ in range(start):
                skip_func(obj, *args, **kwargs)

            # now do actual parsing
            retval = func(obj, *args, **kwargs)
            while not check_none(retval):
                append(retval)
                if len(retvals) >= stop:
                    # quick exit
                    break
                retval = func(obj, *args, **kwargs)

            if len(retvals) == start:
                # none has been found
                return None

        # ensure the next call won't use this key
        # This will prohibit the use
        # tmp = sile.read_geometry[:10]
        # tmp() # will return the first 10
        # tmp() # will return the default (single) item
        self.key = None
        if isinstance(key, Integral):
            return retvals[key]

        # else postprocess
        return self.postprocess(retvals[key])


class SileBound:
    """A bound method deferring stuff to the function

    This class calls the function `func` when directly called
    but returns the `slicer` class when users slices this object.
    """

    def __init__(
        self,
        obj: Type[Any],
        func: Callable[..., Any],
        *,
        slicer: Type[SileSlicer] = SileSlicer,
        default_slice: Optional[Any] = None,
        **kwargs,
    ):
        self._obj = obj
        # first update to the wrapped function
        update_wrapper(self, func)
        self.slicer = slicer
        self.default_slice = default_slice
        self.kwargs = kwargs
        self._update_doc()

    def __str__(self):
        # trying to bypass the documentationt
        return self.__doc__

    def _update_doc(self):
        # Override name to display slice handling in help
        default_slice = self.default_slice
        if self.default_slice is None:
            default_slice = 0

        name = self.__wrapped__.__name__
        self.__name__ = f"{name}[...|{default_slice!r}]"
        try:
            doc = dedent(self.__doc__)
        except AttributeError:
            doc = ""

        if default_slice == 0:
            default_slice = "the first"
        elif default_slice == -1:
            default_slice = "the last"
        elif default_slice == slice(None):
            default_slice = "all"
        else:
            default_slice = self.default_slice

        docs = [doc]
        docs.append(
            dedent(
                f"""
        Notes
        -----
        This method defaults to return {default_slice} item(s).

        This method enables slicing for handling multiple values (see [...|default]).

        This is an optional handler enabling returning multiple elements if {name}
        allows this.

        >>> single = obj.{name}() # returns the default entry of {name}

        To retrieve the first two elements that {name} will return

        >>> first_two = obj.{name}[:2]()

        Retrieving the last two is done equivalently:

        >>> last_two = obj.{name}[-2:]()

        While one can store the sliced function ``tmp = obj.{name}[:]`` one
        will loose the slice after each call.
        """
            )
        )
        doc = "\n".join(docs)
        try:
            self.__doc__ = doc
            self.__call__.__doc__ = doc
        except AttributeError:
            # we cannot set the __doc__ string, let it go
            pass

    def __call__(self, *args, **kwargs):
        if self.default_slice is None:
            return self.__wrapped__(self._obj, *args, **kwargs)
        return self[self.default_slice](*args, **kwargs)

    def __getitem__(self, key):
        """Extract sub items of multiple function calls as an indexed list"""
        return self.slicer(obj=self._obj, func=self.__wrapped__, key=key, **self.kwargs)

    @property
    def next(self):
        """Return the first element of the contained function"""
        return self[0]

    @property
    def last(self):
        """Return the last element of the contained function"""
        return self[-1]


class SileBinder:
    """Bind a class instance to the function name it decorates

    Enables to bypass a class method with another object to defer
    handling in specific cases.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    # this is the decorator call
    def __call__(self, func):
        # update doc str etc.
        update_wrapper(self, func)
        return self

    def __get__(self, obj, objtype=None):
        func = self.__wrapped__

        if obj is None:
            # ensure that we can get documentation
            # and other things, this one won't bind
            # the SileBound object to the function
            # name it arrived from.
            bound = SileBound(obj=objtype, func=func, **self.kwargs)
        else:
            bound = SileBound(obj=obj, func=func, **self.kwargs)
            # bind the class object to the host
            # No more instantiation
            setattr(obj, func.__name__, bound)

        return bound
