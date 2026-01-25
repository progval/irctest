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

IRCU2_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

NEFARIOUS_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	$(EXTRA_SELECTORS)

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

# Tests marked with arbitrary_client_tags or react_tag can't pass because Sable does not support client tags yet
SABLE_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not arbitrary_client_tags \
	and not react_tag \
	$(EXTRA_SELECTORS)

SOLANUM_SELECTORS := \
	not Ergo \
	and not deprecated \
	and not strict \
	and not arbitrary_client_tags \
	$(EXTRA_SELECTORS)

# Same as Limnoria
SOPEL_SELECTORS := \
	(foo or not foo) \
	$(EXTRA_SELECTORS)

# TheLounge can actually pass all the test so there is none to exclude.
# `(foo or not foo)` serves as a `true` value so it doesn't break when
# $(EXTRA_SELECTORS) is non-empty
THELOUNGE_SELECTORS := \
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

.PHONY: all
all: flakes bahamut charybdis ergo inspircd ircu2 nefarious snircd irc2 limnoria mammon sable solanum sopel unrealircd

.PHONY: flakes
flakes:
	find irctest/ -name "*.py" -not -path "irctest/scram/*" -print0 | xargs -0 pyflakes3

.PHONY: bahamut
bahamut:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		-m 'not services' \
		-n 4 \
		-vv -s \
		-m '$(BAHAMUT_SELECTORS)'

.PHONY: bahamut-atheme
bahamut-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(BAHAMUT_SELECTORS)'

.PHONY: bahamut-anope
bahamut-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.bahamut \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(BAHAMUT_SELECTORS)'

.PHONY: charybdis
charybdis:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.charybdis \
		--services-controller=irctest.controllers.atheme_services \
		-m '$(CHARYBDIS_SELECTORS)'

.PHONY: ergo
ergo:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ergo \
		-m "$(ERGO_SELECTORS)"

.PHONY: hybrid
hybrid:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.hybrid \
		--services-controller=irctest.controllers.anope_services \
		-m "$(HYBRID_SELECTORS)"

.PHONY: inspircd
inspircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		-m 'not services and $(INSPIRCD_SELECTORS)'

.PHONY: inspircd-atheme
inspircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(INSPIRCD_SELECTORS)'

.PHONY: inspircd-anope
inspircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.inspircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(INSPIRCD_SELECTORS)'

.PHONY: ircu2
ircu2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.ircu2 \
		-m 'not services and not IRCv3 and $(IRCU2_SELECTORS)'
		-n 4

.PHONY: nefarious
nefarious:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.nefarious \
		-n 4 \
		-m 'not services and $(NEFARIOUS_SELECTORS)'

.PHONY: snircd
snircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.snircd \
		-n 4 \
		-m 'not services and not IRCv3 and $(SNIRCD_SELECTORS)'

.PHONY: irc2
irc2:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.irc2 \
		-n 4 \
		-m 'not services and not IRCv3 and $(IRC2_SELECTORS)'

.PHONY: limnoria
limnoria:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.limnoria \
		-m '$(LIMNORIA_SELECTORS)'

.PHONY: mammon
mammon:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.mammon \
		-m '$(MAMMON_SELECTORS)'

.PHONY: plexus4
plexus4:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.plexus4 \
		--services-controller=irctest.controllers.anope_services \
		-m "$(PLEXUS4_SELECTORS)"

.PHONY: ngircd
ngircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		-n 4 \
		-m énot services and $(NGIRCD_SELECTORS)"

.PHONY: ngircd-anope
ngircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(NGIRCD_SELECTORS)"

.PHONY: ngircd-atheme
ngircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller irctest.controllers.ngircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(NGIRCD_SELECTORS)"

.PHONY: sable
sable:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.sable \
		-k "not list and not lusers and not time and not info" \
		-n 20 \
		-m '$(SABLE_SELECTORS)'

.PHONY: solanum
solanum:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.solanum \
		-m 'not services and $(SOLANUM_SELECTORS)'

.PHONY: solanum
solanum-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.solanum \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services and $(SOLANUM_SELECTORS)'

.PHONY: solanum
solanum-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.solanum \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(SOLANUM_SELECTORS)'

.PHONY: sopel
sopel:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.sopel \
		-m '$(SOPEL_SELECTORS)'

.PHONY: thelounge
thelounge:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.thelounge \
		-m '$(THELOUNGE_SELECTORS)'

.PHONY: unrealircd
unrealircd:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		-m 'not services' \
		-m '$(UNREALIRCD_SELECTORS)'

.PHONY: unrealircd-5
unrealircd-5: unrealircd

.PHONY: unrealircd-atheme
unrealircd-atheme:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.atheme_services \
		-m 'services' \
		-m '$(UNREALIRCD_SELECTORS)'

.PHONY: unrealircd-anope
unrealircd-anope:
	$(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.anope_services \
		-m 'services and $(UNREALIRCD_SELECTORS)'

.PHONY: unrealircd-dlk
unrealircd-dlk:
	pifpaf run mysql -- $(PYTEST) $(PYTEST_ARGS) \
		--controller=irctest.controllers.unrealircd \
		--services-controller=irctest.controllers.dlk_services \
		-m 'services and $(UNREALIRCD_SELECTORS)'
