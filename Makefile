PYTEST ?= python3 -m pytest

# Extra arguments to pass to pytest (eg. `-n 4` to run in parallel if
# pytest-xdist is installed)
PYTEST_ARGS ?=

# Will be appended at the end of the -k argument to pytest
EXTRA_SELECTORS ?=

# testPlainLarge fails because it doesn't handle split AUTHENTICATE (reported on IRC)
ANOPE_SELECTORS := \
	and not testPlainLarge

# buffering tests cannot pass because of issues with UTF-8 handling: https://github.com/DALnet/bahamut/issues/196
BAHAMUT_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not IRCv3 \
	and not buffering \
	$(EXTRA_SELECTORS)

# testQuitErrors is very flaky
# AccountTagTestCase.testInvite fails because https://github.com/solanum-ircd/solanum/issues/166
CHARYBDIS_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testDoubleKickMessages \
	and not testQuitErrors \
	and not (AccountTagTestCase and testInvite) \
	$(EXTRA_SELECTORS)

ERGO_SELECTORS := \
	not deprecated \
	$(EXTRA_SELECTORS)

HYBRID_SELECTORS := \
	not Ergo \
	and not deprecated \
	$(EXTRA_SELECTORS)

# testNoticeNonexistentChannel fails because of https://github.com/inspircd/inspircd/issues/1849
# testBotPrivateMessage and testBotChannelMessage fail because https://github.com/inspircd/inspircd/pull/1910 is not released yet
# testNamesInvalidChannel and testNamesNonexistingChannel fail because https://github.com/inspircd/inspircd/pull/1922 is not released yet.
INSPIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testNoticeNonexistentChannel \
	and not testBotPrivateMessage and not testBotChannelMessage \
	and not testNamesInvalidChannel and not testNamesNonexistingChannel \
	$(EXTRA_SELECTORS)

# buffering tests fail because ircu2 discards the whole buffer on long lines (TODO: refine how we exclude these tests)
# testQuit and testQuitErrors fail because ircu2 does not send ERROR or QUIT
# lusers tests fail because they depend on Modern behavior, not just RFC2812 (TODO: update lusers tests to accept RFC2812-compliant implementations)
# statusmsg tests fail because STATUSMSG is present in ISUPPORT, but it not actually supported as PRIVMSG target
IRCU2_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not buffering \
	and not testQuit \
	and not lusers \
	and not statusmsg \
	$(EXTRA_SELECTORS)

# same justification as ircu2
SNIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not buffering \
	and not testQuit \
	and not lusers \
	and not statusmsg \
	$(EXTRA_SELECTORS)

# testListEmpty and testListOne fails because irc2 deprecated LIST
IRC2_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testListEmpty and not testListOne \
	$(EXTRA_SELECTORS)

MAMMON_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

# Limnoria can actually pass all the test so there is none to exclude.
# `(foo or not foo)` serves as a `true` value so it doesn't break when
# $(EXTRA_SELECTORS) is non-empty
LIMNORIA_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

# testQuitErrors is too flaky for CI
SOLANUM_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testDoubleKickMessages \
	and not testQuitErrors \
	$(EXTRA_SELECTORS)

SOPEL_SELECTORS := \
	not testPlainNotAvailable \
	$(EXTRA_SELECTORS)

# testNoticeNonexistentChannel fails: https://bugs.unrealircd.org/view.php?id=5949
# regressions::testTagCap fails: https://bugs.unrealircd.org/view.php?id=5948
# messages::testLineTooLong fails: https://bugs.unrealircd.org/view.php?id=5947
# testCapRemovalByClient and testNakWhole fail pending https://github.com/unrealircd/unrealircd/pull/148
# Tests marked with arbitrary_client_tags can't pass because Unreal whitelists which tags it relays
# Tests marked with react_tag can't pass because Unreal blocks +draft/react https://github.com/unrealircd/unrealircd/pull/149
# Tests marked with private_chathistory can't pass because Unreal does not implement CHATHISTORY for DMs
# testChathistory[BETWEEN] fails: https://bugs.unrealircd.org/view.php?id=5952
# testChathistory[AROUND] fails: https://bugs.unrealircd.org/view.php?id=5953
UNREALIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testNoticeNonexistentChannel \
	and not (regressions.py and testTagCap) \
	and not (messages.py and testLineTooLong) \
	and not (cap.py and (testCapRemovalByClient or testNakWhole)) \
	and not (account_tag.py and testInvite) \
	and not arbitrary_client_tags \
	and not react_tag \
	and not private_chathistory \
	and not (testChathistory and (between or around)) \
	$(EXTRA_SELECTORS)

.PHONY: all flakes bahamut charybdis ergo inspircd ircu2 snircd irc2 mammon limnoria sopel solanum unrealircd

all: flakes bahamut charybdis ergo inspircd ircu2 snircd irc2 mammon limnoria sopel solanum unrealircd

flakes:
	find irctest/ -name "*.py" -not -path "irctest/scram/*" -print0 | xargs -0 pyflakes3

bahamut:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		-m 'not services' \
		-n 10 \
		-k '$(BAHAMUT_SELECTORS)'

bahamut-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services' \
		-n 10 \
		-k '$(BAHAMUT_SELECTORS)'

bahamut-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.anope_services \
		-m 'services' \
		-n 10 \
		-k '$(BAHAMUT_SELECTORS) $(ANOPE_SELECTORS)'

charybdis:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.charybdis \
		--services-controller=irctest.controllers.atheme_services \
		-k '$(CHARYBDIS_SELECTORS)'

ergo:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ergo \
		-k "$(ERGO_SELECTORS)"

hybrid:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.hybrid \
		-m 'not services' \
		-k "$(HYBRID_SELECTORS)"

inspircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		-m 'not services' \
		-k '$(INSPIRCD_SELECTORS)'

inspircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services' \
		-k '$(INSPIRCD_SELECTORS)'

inspircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services' \
		-k '$(INSPIRCD_SELECTORS) $(ANOPE_SELECTORS)'

ircu2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.ircu2 \
		-m 'not services and not IRCv3' \
		-n 10 \
		-k '$(IRCU2_SELECTORS)'

snircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.snircd \
		-m 'not services and not IRCv3' \
		-n 10 \
		-k '$(SNIRCD_SELECTORS)'

irc2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.irc2 \
		-m 'not services and not IRCv3' \
		-n 10 \
		-k '$(IRC2_SELECTORS)'

limnoria:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.limnoria \
		-k '$(LIMNORIA_SELECTORS)'

mammon:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.mammon \
		-k '$(MAMMON_SELECTORS)'

plexus4:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.plexus4 \
		-m 'not services' \
		-k "$(HYBRID_SELECTORS)"

solanum:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.solanum \
		--services-controller=irctest.controllers.atheme_services \
		-k '$(SOLANUM_SELECTORS)'

sopel:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.sopel \
		-k '$(SOPEL_SELECTORS)'

unrealircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		-m 'not services' \
		-k '$(UNREALIRCD_SELECTORS)'

unrealircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services' \
		-k '$(UNREALIRCD_SELECTORS)'

unrealircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services' \
		-k '$(UNREALIRCD_SELECTORS) $(ANOPE_SELECTORS)'
