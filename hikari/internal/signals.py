# -*- coding: utf-8 -*-
# cython: language_level=3
# Copyright (c) 2020 Nekokatt
# Copyright (c) 2021-present davfsa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Signal handling utilities."""

from __future__ import annotations

__all__: typing.Sequence[str] = ("handle_interrupts",)

import asyncio
import contextlib
import logging
import signal
import threading
import traceback
import types
import typing

from hikari import errors
from hikari.internal import ux

_INTERRUPT_SIGNALS: typing.Tuple[str, ...] = ("SIGINT", "SIGTERM")
_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.signals")


@contextlib.contextmanager
def handle_interrupts(
    enabled: typing.Optional[bool],
    loop: asyncio.AbstractEventLoop,
    exit_callback: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]],
) -> typing.Generator[None, None, None]:
    """Context manager which cleanly exits on signal interrupts.

    Parameters
    ----------
    enabled : typing.Optional[bool]
        Whether to enable the signal interrupts.

        If set to `None`, then it will be enabled or not based on whether the running
        thread is the main one or not.
    loop : asyncio.AbstractEventLoop
        The event loop to run the callback in.
    exit_callback : typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]
        The async callback to call when abruptly exiting the context manager.

        This could be due to an exception or a signal interrupt.
    """
    if enabled is None:
        enabled = threading.current_thread() is threading.main_thread()

    if not enabled:
        # NOOP context manager
        yield
        return

    loop_thread_id = threading.get_native_id()
    interrupt: typing.Optional[errors.HikariInterrupt] = None
    exit_callback_called = False

    def interrupt_handler(signum: int, frame: typing.Optional[types.FrameType]) -> None:
        signame = signal.strsignal(signum)
        assert signame is not None  # Will always be True

        nonlocal interrupt, exit_callback_called
        interrupt = errors.HikariInterrupt(signum, signame)

        # The loop may or may not be running, depending on the state of the application when this occurs.
        # Signals on POSIX only occur on the main thread usually, too, so we need to ensure this is
        # threadsafe.
        # We log native thread IDs purely for debugging purposes.
        if _LOGGER.isEnabledFor(ux.TRACE):
            _LOGGER.log(
                ux.TRACE,
                "interrupt %s occurred on thread %s, process on thread %s will be notified shortly\n"
                "Stacktrace for developer sanity:\n%s",
                signum,
                threading.get_native_id(),
                loop_thread_id,
                "".join(traceback.format_stack(frame)),
            )

        if not exit_callback_called:
            asyncio.run_coroutine_threadsafe(exit_callback(), loop)
            exit_callback_called = True

    for sig in _INTERRUPT_SIGNALS:
        try:
            signum = getattr(signal, sig)
            signal.signal(signum, interrupt_handler)
        except AttributeError:
            _LOGGER.log(ux.TRACE, "signal %s is not implemented on your platform; skipping", sig)

    try:
        yield

    except Exception:
        if not exit_callback_called:
            loop.run_until_complete(exit_callback())
            exit_callback_called = True

        raise

    finally:
        for sig in _INTERRUPT_SIGNALS:
            try:
                signum = getattr(signal, sig)
                signal.signal(signum, signal.SIG_DFL)
            except AttributeError:
                # Signal not implemented. We already logged this earlier.
                pass

        if interrupt:
            raise interrupt
