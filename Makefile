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
# mask tests in test_who.py fail because they are not implemented.
# some HelpTestCase::*[HELP] tests fail because Bahamut forwards /HELP to HelpServ (but not /HELPOP)
BAHAMUT_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not IRCv3 \
	and not buffering \
	and not (testWho and not whois and mask) \
	and not testWhoStar \
	and (not HelpTestCase or HELPOP) \
	$(EXTRA_SELECTORS)

# testQuitErrors is very flaky
# AccountTagTestCase.testInvite fails because https://github.com/solanum-ircd/solanum/issues/166
# testKickDefaultComment fails because it uses the nick of the kickee rather than the kicker.
# testWhoisNumerics[oper] fails because charybdis uses RPL_WHOISSPECIAL instead of RPL_WHOISOPERATOR
CHARYBDIS_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testQuitErrors \
	and not testKickDefaultComment \
	and not (AccountTagTestCase and testInvite) \
	and not (testWhoisNumerics and oper) \
	$(EXTRA_SELECTORS)

# testInfoNosuchserver does not apply to Ergo: Ergo ignores the optional <target> argument
ERGO_SELECTORS := \
	not deprecated \
	and not testInfoNosuchserver \
	$(EXTRA_SELECTORS)

# testInviteUnoppedModern is the only strict test that Hybrid fails
HYBRID_SELECTORS := \
	not Ergo \
	and not testInviteUnoppedModern \
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
# lusers "full" tests fail because they depend on Modern behavior, not just RFC2812
# statusmsg tests fail because STATUSMSG is present in ISUPPORT, but it not actually supported as PRIVMSG target
# testKeyValidation[empty] fails because ircu2 returns ERR_NEEDMOREPARAMS on empty keys: https://github.com/UndernetIRC/ircu2/issues/13
# testKickDefaultComment fails because it uses the nick of the kickee rather than the kicker.
# testEmptyRealname fails because it uses a default value instead of ERR_NEEDMOREPARAMS.
# HelpTestCase fails because it returns NOTICEs instead of numerics
IRCU2_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not buffering \
	and not testQuit \
	and not (lusers and full) \
	and not statusmsg \
	and not (testKeyValidation and empty) \
	and not testKickDefaultComment \
	and not testEmptyRealname \
	and not HelpTestCase \
	$(EXTRA_SELECTORS)

# same justification as ircu2
SNIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not buffering \
	and not testQuit \
	and not (lusers and full) \
	and not statusmsg \
	$(EXTRA_SELECTORS)

# testListEmpty and testListOne fails because irc2 deprecated LIST
# testKickDefaultComment fails because it uses the nick of the kickee rather than the kicker.
# testWallopsPrivileges fails because it ignores the command instead of replying ERR_UNKNOWNCOMMAND
# HelpTestCase fails because it returns NOTICEs instead of numerics
IRC2_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testListEmpty and not testListOne \
	and not testKickDefaultComment \
	and not testWallopsPrivileges \
	and not HelpTestCase \
	$(EXTRA_SELECTORS)

MAMMON_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

# testKeyValidation[spaces] and testKeyValidation[empty] fail because ngIRCd does not validate them https://github.com/ngircd/ngircd/issues/290
# testStarNick: wat
# testEmptyRealname fails because it uses a default value instead of ERR_NEEDMOREPARAMS.
# chathistory tests fail because they need nicks longer than 9 chars
# HelpTestCase::*[HELP] fails because it returns NOTICEs instead of numerics
NGIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not (testKeyValidation and (spaces or empty)) \
	and not testStarNick \
	and not testEmptyRealname \
	and not chathistory \
	and (not HelpTestCase or HELPOP) \
	$(EXTRA_SELECTORS)

# testInviteUnoppedModern is the only strict test that Plexus4 fails
# testInviteInviteOnlyModern fails because Plexus4 allows non-op to invite if (and only if) the channel is not invite-only
PLEXUS4_SELECTORS := \
	not Ergo \
	and not testInviteUnoppedModern \
	and not testInviteInviteOnlyModern \
	and not deprecated \
	$(EXTRA_SELECTORS)

# Limnoria can actually pass all the test so there is none to exclude.
# `(foo or not foo)` serves as a `true` value so it doesn't break when
# $(EXTRA_SELECTORS) is non-empty
LIMNORIA_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

# testQuitErrors is too flaky for CI
# testKickDefaultComment fails because solanum uses the nick of the kickee rather than the kicker.
SOLANUM_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not testQuitErrors \
	and not testKickDefaultComment \
	$(EXTRA_SELECTORS)

SOPEL_SELECTORS := \
	not testPlainNotAvailable \
	$(EXTRA_SELECTORS)

# TheLounge can actually pass all the test so there is none to exclude.
# `(foo or not foo)` serves as a `true` value so it doesn't break when
# $(EXTRA_SELECTORS) is non-empty
THELOUNGE_SELECTORS := \
	(foo or not foo) \
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
# testWhoAllOpers fails because Unreal skips results when the mask is too broad
# HELP and HELPOP tests fail because Unreal uses custom numerics https://github.com/unrealircd/unrealircd/pull/184
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
	and not testWhoAllOpers \
	and not HelpTestCase \
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
		--services-controller=irctest.controllers.anope_services \
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
		--services-controller=irctest.controllers.anope_services \
		-k "$(PLEXUS4_SELECTORS)"

ngircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		-m 'not services' \
		-n 10 \
		-k "$(NGIRCD_SELECTORS)"

ngircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services' \
		-k "$(NGIRCD_SELECTORS)"

ngircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services' \
		-k "$(NGIRCD_SELECTORS)"

solanum:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.solanum \
		--services-controller=irctest.controllers.atheme_services \
		-k '$(SOLANUM_SELECTORS)'

sopel:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.sopel \
		-k '$(SOPEL_SELECTORS)'

thelounge:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.thelounge \
		-k '$(THELOUNGE_SELECTORS)'

unrealircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		-m 'not services' \
		-k '$(UNREALIRCD_SELECTORS)'

unrealircd-5: unrealircd

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
