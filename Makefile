PYTEST ?= python3 -m pytest

# Extra arguments to pass to pytest (eg. `-n 4` to run in parallel if
# pytest-xdist is installed)
PYTEST_ARGS ?=

# Will be appended at the end of the -k argument to pytest
EXTRA_SELECTORS ?=

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

# testNoticeNonexistentChannel fails because of https://github.com/inspircd/inspircd/issues/1849
# testDirectMessageEcho fails because of https://github.com/inspircd/inspircd/issues/1851
# testKeyValidation fails because of https://github.com/inspircd/inspircd/issues/1850
# testBotPrivateMessage and testBotChannelMessage fail because https://github.com/inspircd/inspircd/pull/1910 is not released yet
INSPIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testNoticeNonexistentChannel \
	and not testDirectMessageEcho \
	and not testKeyValidation \
	and not testBotPrivateMessage and not testBotChannelMessage \
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

SOLANUM_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testDoubleKickMessages \
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
	$(PYTEST) $(PYTEST_ARGS) --controller=irctest.controllers.charybdis -k '$(CHARYBDIS_SELECTORS)'

ergo:
	$(PYTEST) $(PYTEST_ARGS) --controller irctest.controllers.ergo -k "$(ERGO_SELECTORS)"

inspircd:
	$(PYTEST) $(PYTEST_ARGS) --controller=irctest.controllers.inspircd -k '$(INSPIRCD_SELECTORS)'

limnoria:
	$(PYTEST) $(PYTEST_ARGS) --controller=irctest.controllers.limnoria -k '$(LIMNORIA_SELECTORS)'

mammon:
	$(PYTEST) $(PYTEST_ARGS) --controller=irctest.controllers.mammon -k '$(MAMMON_SELECTORS)'

solanum:
	$(PYTEST) $(PYTEST_ARGS) --controller=irctest.controllers.solanum -k '$(SOLANUM_SELECTORS)'

sopel:
	$(PYTEST) $(PYTEST_ARGS) --controller=irctest.controllers.sopel -k '$(SOPEL_SELECTORS)'

unrealircd:
	$(PYTEST) $(PYTEST_ARGS) --controller=irctest.controllers.unrealircd -k '$(UNREALIRCD_SELECTORS)'
