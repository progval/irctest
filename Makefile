PYTEST ?= python3 -m pytest

# Extra arguments to pass to pytest (eg. `-n 4` to run in parallel if
# pytest-xdist is installed)
PYTEST_ARGS ?=

# Will be appended at the end of the -m argument to pytest
EXTRA_MARKERS ?=

# Will be appended at the end of the -k argument to pytest
EXTRA_SELECTORS ?=

BAHAMUT_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	and not IRCv3 \
	$(EXTRA_MARKERS)
BAHAMUT_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

CHARYBDIS_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	$(EXTRA_MARKERS)
CHARYBDIS_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

ERGO_MARKERS := \
	(Ergo or not implementation-specific) \
	and not deprecated \
	$(EXTRA_MARKERS)
ERGO_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

HYBRID_MARKERS := \
	not implementation-specific \
	and not deprecated \
	$(EXTRA_MARKERS)
HYBRID_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

INSPIRCD_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	$(EXTRA_MARKERS)
INSPIRCD_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

IRCU2_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	and not IRCv3 \
	$(EXTRA_MARKERS)
IRCU2_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

NEFARIOUS_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	$(EXTRA_MARKERS)
NEFARIOUS_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

SNIRCD_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	and not IRCv3 \
	$(EXTRA_MARKERS)
SNIRCD_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

IRC2_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	and not IRCv3 \
	$(EXTRA_MARKERS)
IRC2_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

MAMMON_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	$(EXTRA_MARKERS)
MAMMON_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

NGIRCD_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	$(EXTRA_MARKERS)
NGIRCD_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

PLEXUS4_MARKERS := \
	not implementation-specific \
	and not deprecated \
	$(EXTRA_MARKERS)
PLEXUS4_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

LIMNORIA_MARKERS := \
	not implementation-specific \
	$(EXTRA_MARKERS)
LIMNORIA_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

# Tests marked with arbitrary_client_tags or react_tag can't pass because Sable does not support client tags yet
# 'SablePostgresqlHistoryTestCase and private_chathistory' disabled because Sable does not (yet?) persist private messages to postgresql
SABLE_MARKERS := \
	(Sable or not implementation-specific) \
	and not deprecated \
	and not strict \
	and not arbitrary_client_tags \
	and not react_tag \
	$(EXTRA_MARKERS)
SABLE_SELECTORS := \
	not list and not lusers and not time and not info \
	and not (SablePostgresqlHistoryTestCase and private_chathistory) \
	$(EXTRA_SELECTORS)

SOLANUM_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	$(EXTRA_MARKERS)
SOLANUM_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

SOPEL_MARKERS := \
	not implementation-specific \
	$(EXTRA_MARKERS)
SOPEL_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

THELOUNGE_MARKERS := \
	not implementation-specific \
	$(EXTRA_MARKERS)
THELOUNGE_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

# Tests marked with arbitrary_client_tags can't pass because Unreal whitelists which tags it relays
# Tests marked with react_tag can't pass because Unreal blocks +draft/react https://github.com/unrealircd/unrealircd/pull/149
# Tests marked with private_chathistory can't pass because Unreal does not implement CHATHISTORY for DMs

UNREALIRCD_MARKERS := \
	not implementation-specific \
	and not deprecated \
	and not strict \
	and not arbitrary_client_tags \
	and not react_tag \
	and not private_chathistory \
	$(EXTRA_MARKERS)
UNREALIRCD_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

.PHONY: all flakes bahamut charybdis ergo inspircd ircu2 snircd irc2 mammon nefarious limnoria sable sopel solanum unrealircd

all: flakes bahamut charybdis ergo inspircd ircu2 snircd irc2 mammon nefarious limnoria sable sopel solanum unrealircd

flakes:
	find irctest/ -name "*.py" -not -path "irctest/scram/*" -print0 | xargs -0 pyflakes3

bahamut:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		-m 'not services' \
		-n 4 \
		-vv -s \
		-m 'not services and $(BAHAMUT_MARKERS)'
		-k '$(BAHAMUT_SELECTORS)'

bahamut-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(BAHAMUT_MARKERS)' \
		-k '$(BAHAMUT_SELECTORS)'

bahamut-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(BAHAMUT_MARKERS)' \
		-k '$(BAHAMUT_SELECTORS)'

charybdis:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.charybdis \
		--services-controller=irctest.controllers.atheme_services \
		-m '$(CHARYBDIS_MARKERS)'
		-k '$(CHARYBDIS_SELECTORS)'

ergo:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ergo \
		-m '$(ERGO_MARKERS)'
		-k "$(ERGO_SELECTORS)"

hybrid:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.hybrid \
		--services-controller=irctest.controllers.anope_services \
		-m '$(HYBRID_MARKERS)'
		-k "$(HYBRID_SELECTORS)"

inspircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		-m 'not services and $(INSPIRCD_MARKERS)' \
		-k '$(INSPIRCD_SELECTORS)'

inspircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(INSPIRCD_MARKERS)' \
		-k '$(INSPIRCD_SELECTORS)'

inspircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(INSPIRCD_MARKERS)' \
		-k '$(INSPIRCD_SELECTORS)'

ircu2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.ircu2 \
		-m 'not services and $(IRCU2_MARKERS)' \
		-n 4 \
		-k '$(IRCU2_SELECTORS)'

nefarious:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.nefarious \
		-m 'not services and $(NEFARIOUS_MARKERS)' \
		-n 4 \
		-k '$(NEFARIOUS_SELECTORS)'

snircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.snircd \
		-m 'not services and $(SNIRCD_MARKERS)' \
		-n 4 \
		-k '$(SNIRCD_SELECTORS)'

irc2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.irc2 \
		-m 'not services and $(IRCU2_MARKERS)' \
		-n 4 \
		-k '$(IRC2_SELECTORS)'

limnoria:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.limnoria \
		-m '$(LIMNORIA_MARKERS)' \
		-k '$(LIMNORIA_SELECTORS)'

mammon:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.mammon \
		-m '$(MAMMON_MARKERS)' \
		-k '$(MAMMON_SELECTORS)'

plexus4:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.plexus4 \
		--services-controller=irctest.controllers.anope_services \
		-m '$(PLEXUS4_MARKERS)' \
		-k "$(PLEXUS4_SELECTORS)"

ngircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		-m 'not services and $(NGIRCD_MARKERS)' \
		-n 4 \
		-k "$(NGIRCD_SELECTORS)"

ngircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(NGIRCD_MARKERS)' \
		-k "$(NGIRCD_SELECTORS)"

ngircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(NGIRCD_MARKERS)' \
		-k "$(NGIRCD_SELECTORS)"

sable:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.sable \
		-m '$(SABLE_MARKERS)' \
		-n 20 \
		-k '$(SABLE_SELECTORS)'

solanum:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.solanum \
		--services-controller=irctest.controllers.atheme_services \
		-m '$(SOLANUM_MARKERS)' \
		-k '$(SOLANUM_SELECTORS)'

sopel:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.sopel \
		-m '$(SOPEL_MARKERS)' \
		-k '$(SOPEL_SELECTORS)'

thelounge:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.thelounge \
		-m '$(THELOUNGE_MARKERS)' \
		-k '$(THELOUNGE_SELECTORS)'

unrealircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		-m 'not services and $(UNREALIRCD_MARKERS)' \
		-k '$(UNREALIRCD_SELECTORS)'

unrealircd-5: unrealircd

unrealircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(UNREALIRCD_MARKERS)' \
		-k '$(UNREALIRCD_SELECTORS)'

unrealircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(UNREALIRCD_MARKERS)' \
		-k '$(UNREALIRCD_SELECTORS)'

unrealircd-dlk:
	pifpaf run mysql -- $(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.dlk_services \
		-m 'services and $(UNREALIRCD_MARKERS)' \
		-k '$(UNREALIRCD_SELECTORS)'
