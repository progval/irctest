"""
Account extended ban (`IRCv3 account-extban
<https://ircv3.net/specs/extensions/account-extban>`__)
"""

from contextlib import contextmanager
from typing import Generator, List, Tuple

from irctest import cases, runner
from irctest.numerics import ERR_BANNEDFROMCHAN
from irctest.specifications import OptionalBehaviors


@cases.mark_services
class AccountExtbanTestCase(cases.BaseServerTestCase):
    """Tests for the IRCv3 account-extban specification.

    https://ircv3.net/specs/extensions/account-extban
    """

    def _account_extban_prefixes(self) -> List[Tuple[str, str]]:
        """Return ``[(prefix, name), ...]`` for every account extban name
        advertised by the server via ``ACCOUNTEXTBAN``.

        The prefix is taken from the ``EXTBAN`` token.

        Raises ``IsupportTokenNotSupported`` when ``ACCOUNTEXTBAN`` is absent.
        """
        assert self.server_support is not None

        if "ACCOUNTEXTBAN" not in self.server_support:
            raise runner.IsupportTokenNotSupported("ACCOUNTEXTBAN")

        extban_token = self.server_support.get("EXTBAN") or ""
        prefix, _, _ = extban_token.partition(",")

        accountextban = self.server_support["ACCOUNTEXTBAN"] or ""
        names = [n for n in accountextban.split(",") if n]

        if not names:
            raise runner.IsupportTokenNotSupported("ACCOUNTEXTBAN")

        return [(prefix, name) for name in names]

    @contextmanager
    def _connect_bob(self, authenticated: bool = True) -> Generator[None, None, None]:
        """Connect a client named ``bob``, yield, then disconnect.

        Drains any post-connect messages (e.g. NickServ MODE +r).
        """
        if authenticated:
            self.connectClient(
                "bob",
                name="bob",
                capabilities=["sasl"],
                account="bob",
                password="sesame",
            )
        else:
            self.connectClient("bob", name="bob")
        self.getMessages("bob")
        try:
            yield
        finally:
            self.clients.pop("bob")

    def _assert_join_allowed(self, chan: str) -> None:
        """Assert that ``bob`` can JOIN *chan*."""
        self.sendLine("bob", f"JOIN {chan}")
        self.assertMessageMatch(self.getMessage("bob"), command="JOIN")

    def _assert_join_banned(self, chan: str) -> None:
        """Assert that ``bob`` is banned from joining *chan*."""
        self.sendLine("bob", f"JOIN {chan}")
        self.assertMessageMatch(self.getMessage("bob"), command=ERR_BANNEDFROMCHAN)

    @cases.mark_specifications("IRCv3")
    def testISupportToken(self):
        """Test that ACCOUNTEXTBAN is advertised and consistent with EXTBAN.

        "Servers publishing the ACCOUNTEXTBAN token MUST also publish
        the EXTBAN token."
        -- <https://ircv3.net/specs/extensions/account-extban>
        """
        self.connectClient("check")

        if "ACCOUNTEXTBAN" not in self.server_support:
            raise runner.IsupportTokenNotSupported("ACCOUNTEXTBAN")

        self.assertIn(
            "EXTBAN",
            self.server_support,
            "ACCOUNTEXTBAN present but EXTBAN missing",
        )

    @cases.mark_specifications("IRCv3")
    def testAccountExtbanJoin(self):
        """Test that an account extban prevents the matching account from
        joining, and that removing it allows them to join again.

        "Servers publishing the ACCOUNTEXTBAN token allow clients to
        construct ban masks matching account names."
        -- <https://ircv3.net/specs/extensions/account-extban>
        """
        self.controller.registerUser(self, "bob", "sesame")
        self.connectClient("chanop", name="chanop")

        for prefix, name in self._account_extban_prefixes():
            chan = f"#chan-{name}"
            mask = f"{prefix}{name}:bob"

            self.joinChannel("chanop", chan)
            self.getMessages("chanop")
            self.sendLine("chanop", f"MODE {chan} +b {mask}")
            self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

            with self._connect_bob():
                self._assert_join_banned(chan)

                # Remove ban — bob can now join
                self.sendLine("chanop", f"MODE {chan} -b {mask}")
                self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

                self._assert_join_allowed(chan)

    @cases.mark_specifications("IRCv3")
    def testAccountExtbanUnauthed(self):
        """Test that an account extban does NOT match an unauthenticated user
        whose nick happens to be the banned account name.

        Account extbans match *accounts*, not nicknames.
        """
        self.connectClient("chanop", name="chanop")

        for prefix, name in self._account_extban_prefixes():
            chan = f"#uchan-{name}"
            mask = f"{prefix}{name}:bob"

            self.joinChannel("chanop", chan)
            self.getMessages("chanop")
            self.sendLine("chanop", f"MODE {chan} +b {mask}")
            self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

            with self._connect_bob(authenticated=False):
                self._assert_join_allowed(chan)

    @cases.mark_specifications("IRCv3")
    def testAccountExtbanException(self):
        """Test that a ban exception (+e) with an account extban allows a
        banned account to join despite a broad hostmask ban.

        Requires EXCEPTS / mode ``e`` support.
        """
        self.controller.registerUser(self, "bob", "sesame")
        self.connectClient("chanop", name="chanop")

        if "EXCEPTS" in self.server_support:
            mode = self.server_support["EXCEPTS"] or "e"
        else:
            if (
                "CHANMODES" in self.server_support
                and "e" in self.server_support["CHANMODES"]
            ):
                mode = "e"
            else:
                raise runner.OptionalBehaviorNotSupported(
                    OptionalBehaviors.BAN_EXCEPTION_MODE,
                )

        for prefix, name in self._account_extban_prefixes():
            chan = f"#echan-{name}"
            mask = f"{prefix}{name}:bob"

            self.joinChannel("chanop", chan)
            self.getMessages("chanop")

            # Ban everyone
            self.sendLine("chanop", f"MODE {chan} +b *!*@*")
            self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

            # Except bob's account
            self.sendLine("chanop", f"MODE {chan} +{mode} {mask}")
            self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

            with self._connect_bob():
                self._assert_join_allowed(chan)

    @cases.mark_specifications("IRCv3")
    def testAccountExtbanInviteException(self):
        """Test that an invite exception (+I) with an account extban allows
        the matching account to join an invite-only channel.

        Requires INVEX / mode ``I`` support.
        """
        self.controller.registerUser(self, "bob", "sesame")
        self.connectClient("chanop", name="chanop")

        if "INVEX" in self.server_support:
            mode = self.server_support["INVEX"] or "I"
        else:
            if (
                "CHANMODES" in self.server_support
                and "I" in self.server_support["CHANMODES"]
            ):
                mode = "I"
            else:
                raise runner.OptionalBehaviorNotSupported(
                    OptionalBehaviors.INVITE_EXCEPTION_MODE,
                )

        for prefix, name in self._account_extban_prefixes():
            chan = f"#ichan-{name}"
            mask = f"{prefix}{name}:bob"

            self.joinChannel("chanop", chan)
            self.getMessages("chanop")

            # Set invite-only
            self.sendLine("chanop", f"MODE {chan} +i")
            self.getMessages("chanop")

            # Set invite exception for bob's account
            self.sendLine("chanop", f"MODE {chan} +{mode} {mask}")
            self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

            with self._connect_bob():
                self._assert_join_allowed(chan)
