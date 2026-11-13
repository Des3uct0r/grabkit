#!/usr/bin/env python3
"""password_tools.py - generate strong passwords, check the strength of one.

Uses only the Python standard library - nothing to install.

Usage examples:
    python password_tools.py generate
    python password_tools.py generate --length 24 --count 3
    python password_tools.py generate --no-symbols
    python password_tools.py check

'check' asks for the password without echoing it and only reports length,
character classes and an estimated strength - the password itself is never
printed or saved.

Exit codes: 0 = success, 2 = wrong command line usage.
"""

import argparse
import getpass
import math
import secrets
import string
import sys


def _positive_int(value):
    """argparse type: an integer greater than zero."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("'%s' is not a number" % value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive number (got %d)" % number)
    return number


def build_pool(use_symbols, use_digits):
    """Return (character_pool, required_groups) based on the chosen flags.

    required_groups holds at least one character from each enabled class so the
    generated password is guaranteed to use every class the user asked for.
    """
    groups = [string.ascii_lowercase, string.ascii_uppercase]
    if use_digits:
        groups.append(string.digits)
    if use_symbols:
        groups.append("!@#$%^&*()-_=+[]{};:,.?")
    pool = "".join(groups)
    return pool, groups


def generate_password(length, use_symbols, use_digits):
    """Create one random password of the requested length using 'secrets'.

    Guarantees at least one character from each enabled class, then fills the
    rest with fully random picks from the whole pool. The result is shuffled so
    the guaranteed characters are not always at the start.
    """
    pool, groups = build_pool(use_symbols, use_digits)
    if length < len(groups):
        # e.g. length 2 cannot contain lower+upper+digit+symbol; be clear about it.
        print("Error: --length %d is too short to include all requested "
              "character types (%d types)." % (length, len(groups)))
        print("Use at least --length %d, or drop types with --no-digits/--no-symbols."
              % len(groups))
        sys.exit(2)
    chars = [secrets.choice(group) for group in groups]
    chars += [secrets.choice(pool) for _ in range(length - len(groups))]
    # Fisher-Yates shuffle driven by the cryptographically secure RNG.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def cmd_generate(args):
    """Print the requested number of passwords, one per line."""
    for _ in range(args.count):
        print(generate_password(args.length, not args.no_symbols, not args.no_digits))


def cmd_check(args):
    """Read a password invisibly and report its strength. Never echo it."""
    try:
        password = getpass.getpass("Password to check (input is hidden): ")
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    if not password:
        print("No password entered - nothing to check.")
        sys.exit(2)

    length = len(password)
    classes = {
        "lowercase letters": any(c in string.ascii_lowercase for c in password),
        "uppercase letters": any(c in string.ascii_uppercase for c in password),
        "digits": any(c in string.digits for c in password),
        "symbols": any(c in string.punctuation for c in password),
    }
    used = [name for name, present in classes.items() if present]

    # Estimate the alphabet size from the classes actually used, then
    # entropy = length * log2(alphabet_size). This is the standard crude
    # estimate: it assumes every character was picked at random, which real
    # passwords usually are not - so treat it as an upper bound.
    alphabet = 0
    if classes["lowercase letters"]:
        alphabet += 26
    if classes["uppercase letters"]:
        alphabet += 26
    if classes["digits"]:
        alphabet += 10
    if classes["symbols"]:
        alphabet += len(string.punctuation)
    if alphabet == 0:
        alphabet = 1  # degenerate single-character case
    bits = length * math.log2(alphabet) if length > 0 else 0.0

    print("")
    print("Length           : %d" % length)
    print("Character types  : %s" % (", ".join(used) if used else "none"))
    print("Estimated entropy: %.0f bits" % bits)
    print("")

    if length < 8:
        verdict = "VERY WEAK - far too short, crackable almost instantly."
    elif bits < 28:
        verdict = "VERY WEAK - a common cracking rig breaks this in seconds."
    elif bits < 36:
        verdict = "WEAK - fine for a throwaway account, not for anything you care about."
    elif bits < 60:
        verdict = "FAIR - acceptable for low-risk accounts; add length or more character types."
    elif bits < 80:
        verdict = "STRONG - good protection against serious attacks."
    else:
        verdict = "VERY STRONG - excellent length and variety."
    print("Verdict: %s" % verdict)

    tips = []
    if length < 12:
        tips.append("make it longer (12+ characters is a good baseline)")
    if not classes["digits"]:
        tips.append("add a digit")
    if not classes["symbols"]:
        tips.append("add a symbol")
    if not classes["uppercase letters"]:
        tips.append("add an uppercase letter")
    if tips:
        print("To improve: " + "; ".join(tips) + ".")
    # NOTE: we never print or store the password itself.


def main():
    parser = argparse.ArgumentParser(
        prog="password_tools.py",
        description="Generate strong passwords and check how strong a password is.",
        epilog="Examples:\n"
               "  python password_tools.py generate --length 24 --count 3\n"
               "  python password_tools.py generate --no-symbols\n"
               "  python password_tools.py check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    p = sub.add_parser("generate", help="print one or more random passwords")
    p.add_argument("--length", type=_positive_int, default=16,
                   help="password length (default: 16)")
    p.add_argument("--count", type=_positive_int, default=1,
                   help="how many passwords to print (default: 1)")
    p.add_argument("--no-symbols", action="store_true",
                   help="leave out symbols like !@# (some sites reject them)")
    p.add_argument("--no-digits", action="store_true", help="leave out digits 0-9")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("check", help="check a password invisibly and report its strength")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
