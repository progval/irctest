PYTEST ?= python3 -m pytest

# Extra arguments to pass to pytest (eg. `-n 4` to run in parallel if
# pytest-xdist is installed)
PYTEST_ARGS ?=

# Will be appended at the end of the -k argument to pytest
EXTRA_SELECTORS ?=

# testPlainLarge fails because it doesn't handle split AUTHENTICATE (reported on IRC)
ANOPE_SELECTORS := \
	and not testPlainLarge

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
# test_regressions::testTagCap fails: https://bugs.unrealircd.org/view.php?id=5948
# test_messages::testLineTooLong fails: https://bugs.unrealircd.org/view.php?id=5947
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
	and not (test_regressions and testTagCap) \
	and not (test_messages and testLineTooLong) \
	and not (test_cap and (testCapRemovalByClient or testNakWhole)) \
	and not (test_account_tag and testInvite) \
	and not arbitrary_client_tags \
	and not react_tag \
	and not private_chathistory \
	and not (testChathistory and (between or around)) \
	$(EXTRA_SELECTORS)

.PHONY: all flakes charybdis ergo inspircd mammon limnoria sopel solanum unrealircd

all: flakes charybdis ergo inspircd mammon limnoria sopel solanum unrealircd

flakes:
	pyflakes3 irctest

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

limnoria:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.limnoria \
		-k '$(LIMNORIA_SELECTORS)'

mammon:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.mammon \
		-k '$(MAMMON_SELECTORS)'

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
