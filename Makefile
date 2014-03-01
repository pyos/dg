all:   clean js css html
clean: ; find * \( -type d -empty -o -name index.html -o -name '*.pyc' -o -name '*.gen.*' \) -delete

css:   css-site
css-site: ; python3 -m dg build.dg src . /css/site.sass

html:  html-index html-tutorial
html-index:    ; python3 -m dg build.dg src . /index.hamlike
html-tutorial: ; python3 -m dg build.dg src . /tutorial/index.hamlike
