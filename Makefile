# @title TLang Makefile

# === BUILD ASSETS AND ARTIFACTS ==============================================

SOURCES_TXTO   =$(wildcard *.txto docs/*.txto docs/*/.txto docs/*/*.txto docs/*/*/*.txto)
SOURCES_TLANG  =$(wildcard examples/*.tlang)
SOURCES_PY     =$(wildcard src/py/*.py src/py/*/*.py src/py/*/*/*.py research/*.py)
SOURCES_PAML   =$(wildcard src/paml/*.paml)
SOURCES_PCSS   =$(wildcard src/pcss/*.pcss)

BUILD_XML      =\
	$(patsubst %.txto,build/%.xml,$(filter docs/%,$(SOURCES_TXTO))) \
	$(patsubst %.tlang,build/%.xml,$(filter examples/%,$(SOURCES_TLANG)))

BUILD_XSL      =\
	$(patsubst %.xsl.paml,build/%.xsl,$(filter %.xsl.paml,$(SOURCES_PAML)))

BUILD_ALL      =\
	$(BUILD_XML) $(BUID_XSL)

# === SETUP ===================================================================

# General requirements
BUILD_ID      :=$(shell hg id | tr '[:space:]' '-' | cut -d- -f1-2)
SAFE_BUILD_ID :=$(shell hg id | cut -d' ' -f1 | tr -d '+')
TIMESTAMP     :=$(shell date +'%F')
TIME          :=$(shell date -R)
YEAR          :=$(shell date +'%Y')

# REQ:texto:pip install --user texto
TEXTO         :=texto
# REQ:texto:pip install --user polyblocks
POLYBLOCKS    :=polyblocks
# REQ:texto:pip install --user paml
PAML          :=paml
# REQ:texto:pip install --user --upgrade libparsing ctypes pythoniccss
PCSS          :=pcss

REQUIRED_CMD  :=$(TEXTO) $(POLYBLOCKS) $(PAML) $(PCSS)

# === COLORS ==================================================================
YELLOW        :=$(shell echo `tput setaf 226`)
ORANGE        :=$(shell echo `tput setaf 208`)
GREEN         :=$(shell echo `tput setaf 118`)
BLUE          :=$(shell echo `tput setaf 45`)
CYAN          :=$(shell echo `tput setaf 51`)
RED           :=$(shell echo `tput setaf 196`)
GRAY          :=$(shell echo `tput setaf 153`)
GRAYLT        :=$(shell echo `tput setaf 231`)
REGULAR       :=$(shell echo `tput setaf 7`)
RESET         :=$(shell echo `tput sgr0`)
BOLD          :=$(shell echo `tput bold`)
UNDERLINE     :=$(shell echo `tput smul`)
REV           :=$(shell echo `tput rev`)
DIM           :=$(shell echo `tput dim`)

# Returns the parents/ancestors of the the given $(1) path
# FROM <https://stackoverflow.com/questions/16144115/makefile-remove-duplicate-words-without-sorting#16151140>
uniq           =$(if $1,$(firstword $1) $(call uniq,$(filter-out $(firstword $1),$1)))
log_message    =$(info $(BLUE) ▷  $(1)$(RESET))
log_product    =$(info $(GREEN) ◀  $(BOLD)$@$(RESET) $(BLUE)[$(1)]$(RESET))

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

all: $(BUILD_ALL)
	
info:
	$(info $(BUILD_ALL))

# -----------------------------------------------------------------------------
#
# RULES
#
# -----------------------------------------------------------------------------

build/%.xml: %.txto
	$(call log_product,TXTO→XML)
	@mkdir -p `dirname "$@"`
	@$(TEXTO) -Oxml "$<" > "$@"

build/%.xml: %.tlang
	$(call log_product,TLANG→XML)
	@mkdir -p `dirname "$@"`
	@$(POLYBLOCKS) -Oxml "$<" > "$@"

build/lib/xsl/%.xsl: src/paml/%.paml.xsl
	$(call log_product,XSL/PAML→XSL)
	@$(PAML) "$<" > "@"

# === HELPERS =================================================================

print-%:
	@echo "$*="
	@echo "$($*)" | xargs -n1 echo | sort -dr

.FORCE:

# EOF - vim: ts=4 sw=4 noet
