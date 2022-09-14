PYTEST ?= python3 -m pytest

# Extra arguments to pass to pytest (eg. `-n 4` to run in parallel if
# pytest-xdist is installed)
PYTEST_ARGS ?=

# Will be appended at the end of the -k argument to pytest
EXTRA_SELECTORS ?=

BAHAMUT_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not IRCv3 \
	$(EXTRA_SELECTORS)

CHARYBDIS_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

ERGO_SELECTORS := \
	not deprecated \
	$(EXTRA_SELECTORS)

HYBRID_SELECTORS := \
	not Ergo \
	and not deprecated \
	$(EXTRA_SELECTORS)

INSPIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

# HelpTestCase fails because it returns NOTICEs instead of numerics
IRCU2_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

# same justification as ircu2
# lusers "unregistered" tests fail because 
NEFARIOUS_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

# same justification as ircu2
SNIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

IRC2_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

MAMMON_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

NGIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

PLEXUS4_SELECTORS := \
	not Ergo \
	and not deprecated \
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
	$(EXTRA_SELECTORS)

# Same as Limnoria
SOPEL_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

# Tests marked with arbitrary_client_tags can't pass because Unreal whitelists which tags it relays
# Tests marked with react_tag can't pass because Unreal blocks +draft/react https://github.com/unrealircd/unrealircd/pull/149
# Tests marked with private_chathistory can't pass because Unreal does not implement CHATHISTORY for DMs

UNREALIRCD_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not arbitrary_client_tags \
	and not react_tag \
	and not private_chathistory \
	$(EXTRA_SELECTORS)

.PHONY: all flakes bahamut charybdis ergo inspircd ircu2 snircd irc2 mammon nefarious limnoria sopel solanum unrealircd

all: flakes bahamut charybdis ergo inspircd ircu2 snircd irc2 mammon nefarious limnoria sopel solanum unrealircd

flakes:
	find irctest/ -name "*.py" -not -path "irctest/scram/*" -print0 | xargs -0 pyflakes3

bahamut:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		-m 'not services' \
		-n 4 \
		-vv -s \
		-k '$(BAHAMUT_SELECTORS)'

bahamut-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services' \
		-k '$(BAHAMUT_SELECTORS)'

bahamut-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.anope_services \
		-m 'services' \
		-k '$(BAHAMUT_SELECTORS)'

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
		-k '$(INSPIRCD_SELECTORS)'

ircu2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.ircu2 \
		-m 'not services and not IRCv3' \
		-n 4 \
		-k '$(IRCU2_SELECTORS)'

nefarious:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.nefarious \
		-m 'not services' \
		-n 4 \
		-k '$(NEFARIOUS_SELECTORS)'

snircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.snircd \
		-m 'not services and not IRCv3' \
		-n 4 \
		-k '$(SNIRCD_SELECTORS)'

irc2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.irc2 \
		-m 'not services and not IRCv3' \
		-n 4 \
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
		-n 4 \
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
		-k '$(UNREALIRCD_SELECTORS)'

unrealircd-dlk:
	pifpaf run mysql -- $(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.dlk_services \
		-vv \
		-m 'services' \
		-k '$(UNREALIRCD_SELECTORS)'
