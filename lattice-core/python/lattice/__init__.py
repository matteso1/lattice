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

from lattice._core import Signal as _Signal

__version__ = "0.1.0"
__all__ = ["signal", "Signal"]


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

    @property
    def value(self) -> object:
        """Get the current value of the signal."""
        return self._inner.value

    @value.setter
    def value(self, new_value: object) -> None:
        """Set a new value, notifying all dependents."""
        self._inner.value = new_value

    @property
    def id(self) -> int:
        """Get the unique identifier for this signal."""
        return self._inner.id

    def __repr__(self) -> str:
        return f"Signal(value={self.value!r})"


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
