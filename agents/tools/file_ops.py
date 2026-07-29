"""Legacy re-export — implementation lives in aaos.tools.builtins."""

from aaos.tools.builtins.file_ops import (
    read_file,
    write_file,
    list_files,
    delete_file,
)

__all__ = ["read_file", "write_file", "list_files", "delete_file"]
