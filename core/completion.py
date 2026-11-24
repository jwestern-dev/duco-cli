"""Complete registered commands and their locally available arguments."""

import re
import shlex

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import emacs_insert_mode
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.named_commands import get_by_name

from core.commands import REGISTRY
from core.shell import operators


EDITING_KEYS = KeyBindings()


@EDITING_KEYS.add("backspace", filter=emacs_insert_mode)
def refresh_after_backspace(event):
    """
    *refresh_after_backspace Refresh completion candidates after deleting the previous character.*

    event KeyPressEvent - Prompt editing event with the active buffer.
    """
    buffer = event.current_buffer
    get_by_name("backward-delete-char").call(event)
    buffer.start_completion(select_first=False)


# Keep an unfinished quoted argument together while the user is typing it.
_TOKEN = re.compile(r"""(?:[^\s"'\\]+|\\.|"[^"]*(?:"|$)|'[^']*(?:'|$))+""")


class CommandCompleter(Completer):
    """
    *CommandCompleter Suggest registered commands, aliases and context-specific arguments.*
    """
    def get_completions(self, document: Document, complete_event):
        """
        *get_completions Yield replacements for the token at the cursor.*

        document Document - Current input and cursor position.
        complete_event CompleteEvent - Completion request supplied by prompt_toolkit.
        """
        if not document.text.strip():
            return
        # Replacing the prefix in the middle of a word would duplicate its suffix.
        if document.current_char and not document.current_char.isspace():
            return
        before = document.text_before_cursor
        start = 0
        for index, operator in operators(before):
            start = index + len(operator)
        before = before[start:]
        tokens = list(_TOKEN.finditer(before))
        token = tokens.pop().group() if tokens and tokens[-1].end() == len(before) else ""
        context = [part.group() for part in tokens]
        context = [word.lstrip("/").lower() for word in context]
        in_help = context[:1] == ["help"]
        if in_help:
            context = context[1:]

        groups = REGISTRY.categories()
        if not context:
            candidates = set(REGISTRY.names()).union(groups)
        elif len(context) == 1 and context[0] in groups and (in_help or REGISTRY.get(context[0]) is None):
            candidates = {
                name for command in groups[context[0]] for name in (command.name, *command.aliases)
            }
        else:
            if in_help:
                return
            name, *args = context
            command = REGISTRY.get(name)
            qualified = REGISTRY.get(args[0]) if args else None
            if name in groups and args and (command is None or (qualified and qualified.category == name)):
                command = REGISTRY.get(args.pop(0))
                if command is None or command.category != name:
                    return
            if command is None:
                return
            provider = command.completers.get(f"pos{len(args)}")
            if provider:
                values = provider()
            elif "options" in command.completers and (not token or token.startswith("-")):
                values = command.completers["options"](args)
            else:
                return
            prefix = token.lstrip("'\"").casefold()
            for value in sorted(set(values)):
                if value.casefold().startswith(prefix):
                    yield Completion(shlex.quote(value), start_position=-len(token))
            return

        prefix = token.lstrip("/").lower()
        for name in sorted(candidates):
            if name.startswith(prefix):
                yield Completion(name, start_position=-len(prefix))
