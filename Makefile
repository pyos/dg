PYTHON = /usr/bin/env python3
DG     = $(PYTHON) -m dg

SOURCE_DIR = src
TARGET_DIR = .
BUILD      = $(DG) build.dg $(SOURCE_DIR) $(TARGET_DIR)

all:   clean css html
clean: ; find * \( -type d -empty -o -name index.html -o -name '*.pyc' -o -name '*.gen.*' \) -delete

css:   css-site
css-site: ; $(BUILD) /css/site.sass

html:  html-index html-tutorial
html-index:    ; $(BUILD) /index.hamlike
html-repl:     ; $(BUILD) /repl/index.hamlike
html-tutorial: ; $(BUILD) /tutorial/index.hamlike
