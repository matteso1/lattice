"""
Lattice - A reactive Python UI framework with a Rust-powered core.

This package provides the Python interface to the Lattice framework.
The core runtime is implemented in Rust for performance.

Example usage:

    from lattice import signal, memo, effect

    # Create reactive state
    count = signal(0)

    # Create derived values
    @memo
    def doubled():
        return count.value * 2

    # Create side effects
    @effect
    def log_changes():
        print(f"Count: {count.value}, Doubled: {doubled()}")

    # Update state (triggers effects)
    count.value = 5
"""

from typing import Callable, TypeVar, Generic, Optional, Set, Any
from functools import wraps
import threading

from lattice._core import Signal as _Signal

__version__ = "0.1.0"
__all__ = ["signal", "Signal", "memo", "Memo", "effect", "Effect"]


# Thread-local storage for tracking the current reactive context.
# This enables automatic dependency tracking.
_context = threading.local()


def _get_current_context() -> Optional["_ReactiveContext"]:
    """Get the currently active reactive context, if any."""
    stack = getattr(_context, "stack", None)
    if stack:
        return stack[-1]
    return None


def _push_context(ctx: "_ReactiveContext") -> None:
    """Push a reactive context onto the stack."""
    if not hasattr(_context, "stack"):
        _context.stack = []
    _context.stack.append(ctx)


def _pop_context() -> None:
    """Pop the current reactive context from the stack."""
    if hasattr(_context, "stack") and _context.stack:
        _context.stack.pop()


class _ReactiveContext:
    """
    A context that tracks dependencies during reactive computation.
    
    This is an internal class that manages dependency tracking when
    memos and effects access signals.
    """
    
    def __init__(self) -> None:
        self.dependencies: Set["Signal"] = set()
    
    def track(self, signal: "Signal") -> None:
        """Record that we depend on this signal."""
        self.dependencies.add(signal)
    
    def __enter__(self) -> "_ReactiveContext":
        _push_context(self)
        return self
    
    def __exit__(self, *args: Any) -> None:
        _pop_context()


class Signal:
    """
    A reactive signal holding a mutable value.

    Signals are the fundamental reactive primitive. When a signal's value
    is read within a reactive context (such as a memo or effect), the
    signal automatically registers that context as a dependent. When the
    signal's value changes, all dependents are notified.

    Attributes:
        value: The current value of the signal. Getting this value within
            a reactive context establishes a dependency. Setting this value
            notifies all dependents.

    Example:
        >>> count = signal(0)
        >>> print(count.value)
        0
        >>> count.value = 5
        >>> print(count.value)
        5
    """

    def __init__(self, initial_value: object) -> None:
        """
        Create a new signal with the given initial value.

        Args:
            initial_value: The initial value for the signal.
        """
        self._inner = _Signal(initial_value)
        self._dependents: Set[Any] = set()

    @property
    def value(self) -> object:
        """Get the current value of the signal."""
        # Track this signal as a dependency if we're in a reactive context
        ctx = _get_current_context()
        if ctx is not None:
            ctx.track(self)
        return self._inner.value

    @value.setter
    def value(self, new_value: object) -> None:
        """Set a new value, notifying all dependents."""
        self._inner.value = new_value
        # Notify all dependents
        self._notify()
    
    def _subscribe(self, dependent: Any) -> None:
        """Add a dependent to be notified on changes."""
        self._dependents.add(dependent)
    
    def _unsubscribe(self, dependent: Any) -> None:
        """Remove a dependent."""
        self._dependents.discard(dependent)
    
    def _notify(self) -> None:
        """Notify all dependents that the value changed."""
        for dep in list(self._dependents):
            dep._on_dependency_changed()

    @property
    def id(self) -> int:
        """Get the unique identifier for this signal."""
        return self._inner.id

    def __repr__(self) -> str:
        return f"Signal(value={self._inner.value!r})"


T = TypeVar("T")


class Memo(Generic[T]):
    """
    A cached derived value that recomputes only when dependencies change.
    
    Memos are lazy: they only compute their value when accessed. Once
    computed, the value is cached until one of its dependencies changes.
    
    Example:
        >>> count = signal(0)
        >>> @memo
        ... def doubled():
        ...     return count.value * 2
        >>> doubled()  # Computes and caches
        0
        >>> count.value = 5
        >>> doubled()  # Recomputes because count changed
        10
    """
    
    def __init__(self, fn: Callable[[], T]) -> None:
        """
        Create a new memo with the given computation function.
        
        Args:
            fn: A function that computes the memo's value.
        """
        self._fn = fn
        self._value: Optional[T] = None
        self._dirty = True
        self._dependencies: Set[Signal] = set()
    
    def __call__(self) -> T:
        """Get the memo's value, recomputing if necessary."""
        if self._dirty:
            self._recompute()
        return self._value  # type: ignore
    
    def _recompute(self) -> None:
        """Recompute the memo's value and update dependencies."""
        # Clear old subscriptions
        for sig in self._dependencies:
            sig._unsubscribe(self)
        
        # Run computation within a tracking context
        with _ReactiveContext() as ctx:
            self._value = self._fn()
        
        # Subscribe to new dependencies
        self._dependencies = ctx.dependencies
        for sig in self._dependencies:
            sig._subscribe(self)
        
        self._dirty = False
    
    def _on_dependency_changed(self) -> None:
        """Called when one of our dependencies changes."""
        self._dirty = True
    
    def __repr__(self) -> str:
        state = "dirty" if self._dirty else "clean"
        return f"Memo({self._fn.__name__}, {state})"


class Effect:
    """
    A side-effecting computation that runs when dependencies change.
    
    Effects are eager: they run immediately when created and again
    whenever any of their dependencies change.
    
    Example:
        >>> count = signal(0)
        >>> @effect
        ... def log_count():
        ...     print(f"Count is: {count.value}")
        Count is: 0
        >>> count.value = 5
        Count is: 5
    """
    
    def __init__(self, fn: Callable[[], None]) -> None:
        """
        Create a new effect with the given function.
        
        The function runs immediately to establish dependencies.
        
        Args:
            fn: A function to run as a side effect.
        """
        self._fn = fn
        self._dependencies: Set[Signal] = set()
        self._disposed = False
        
        # Run immediately to establish dependencies
        self._run()
    
    def _run(self) -> None:
        """Run the effect and update dependencies."""
        if self._disposed:
            return
        
        # Clear old subscriptions
        for sig in self._dependencies:
            sig._unsubscribe(self)
        
        # Run within a tracking context
        with _ReactiveContext() as ctx:
            self._fn()
        
        # Subscribe to new dependencies
        self._dependencies = ctx.dependencies
        for sig in self._dependencies:
            sig._subscribe(self)
    
    def _on_dependency_changed(self) -> None:
        """Called when one of our dependencies changes."""
        self._run()
    
    def dispose(self) -> None:
        """Stop the effect from running."""
        self._disposed = True
        for sig in self._dependencies:
            sig._unsubscribe(self)
        self._dependencies.clear()
    
    def __repr__(self) -> str:
        state = "disposed" if self._disposed else "active"
        return f"Effect({self._fn.__name__}, {state})"


def signal(initial_value: object) -> Signal:
    """
    Create a new reactive signal with the given initial value.

    This is the preferred way to create signals. It returns a Signal
    instance that can be used to read and write reactive state.

    Args:
        initial_value: The initial value for the signal.

    Returns:
        A new Signal instance.

    Example:
        >>> count = signal(0)
        >>> count.value = 5
        >>> print(count.value)
        5
    """
    return Signal(initial_value)


def memo(fn: Callable[[], T]) -> Memo[T]:
    """
    Create a memoized computed value.
    
    The decorated function is called lazily and its result is cached.
    When any signals accessed during computation change, the cached
    value is invalidated and will be recomputed on next access.
    
    Args:
        fn: A function that computes the derived value.
    
    Returns:
        A Memo instance that can be called to get the value.
    
    Example:
        >>> count = signal(0)
        >>> @memo
        ... def doubled():
        ...     return count.value * 2
        >>> doubled()
        0
    """
    return Memo(fn)


def effect(fn: Callable[[], None]) -> Effect:
    """
    Create a reactive side effect.
    
    The decorated function runs immediately and again whenever any
    signals it accesses change.
    
    Args:
        fn: A function to run as a side effect.
    
    Returns:
        An Effect instance that can be used to dispose the effect.
    
    Example:
        >>> count = signal(0)
        >>> @effect
        ... def log_count():
        ...     print(f"Count: {count.value}")
        Count: 0
        >>> count.value = 1
        Count: 1
    """
    return Effect(fn)
