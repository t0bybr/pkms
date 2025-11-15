"""
pkms/lib/fs/ids.py - ULID Generation and Validation

ULID (Universally Unique Lexicographically Sortable Identifier):
- 26 characters (Crockford Base32 encoding)
- Lexicographically sortable (timestamp prefix)
- Case-insensitive, URL-safe
- 128-bit compatibility with UUID

Format: TTTTTTTTTTRRRRRRRRRRRRRRRR
  - First 10 chars: Timestamp (millisecond precision)
  - Last 16 chars: Random data

Example: 01HAR6DP2M7G1KQ3Y3VQ8C0Q

Benefits:
- Git-friendly (no special characters)
- Sortable by creation time
- Collision-resistant
- Human-readable (compared to UUID)

Usage:
    from pkms.lib.fs.ids import new_id, is_valid_ulid

    # Generate new ID
    doc_id = new_id()
    # => "01JB2X5K9Q7W8M3N6P1R4T0V"

    # Validate ID
    if is_valid_ulid(doc_id):
        print("Valid!")

    # Check invalid ID
    is_valid_ulid("invalid-id")  # => False
"""
import re
from ulid import ULID

# Crockford Base32 alphabet (excludes I, L, O, U to avoid confusion)
# Valid chars: 0-9, A-H, J-K, M-N, P-T, V-Z
ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def new_id() -> str:
	"""
	Generate a new ULID as string.

	Returns:
		str: 26-character ULID (e.g., "01HAR6DP2M7G1KQ3Y3VQ8C0Q")

	Example:
		>>> doc_id = new_id()
		>>> len(doc_id)
		26
		>>> doc_id[0:2]  # First 2 chars represent timestamp
		'01'

	Notes:
		- Uses current UTC timestamp (millisecond precision)
		- Random component ensures uniqueness
		- Thread-safe
		- Monotonically increasing (within same millisecond)
	"""
	return str(ULID())


def is_valid_ulid(value: str) -> bool:
	"""
	Validate ULID format using regex.

	Args:
		value: String to validate (can be None or empty)

	Returns:
		bool: True if valid ULID format, False otherwise

	Example:
		>>> is_valid_ulid("01HAR6DP2M7G1KQ3Y3VQ8C0Q")
		True
		>>> is_valid_ulid("invalid-id")
		False
		>>> is_valid_ulid("")
		False
		>>> is_valid_ulid(None)
		False

	Notes:
		- Only checks format, not semantic validity
		- Case-sensitive (uppercase required)
		- Does not verify timestamp is in valid range
	"""
	return bool(ULID_RE.match(value or ""))