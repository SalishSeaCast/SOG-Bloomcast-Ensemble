# Makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
BUILDDIR      = _build
EOS_HOST	  = sable

# Internal variables.
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(SPHINXOPTS) .
EOS_WEB = /home/sallen/public_html/SOG-docs/SoG-bloomcast/

.PHONY: help clean html

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html        to make standalone HTML files"
	@echo "  rsync-eosn  to rsync HTML files to EOS public web space"

clean:
	-rm -rf $(BUILDDIR)/*

html:
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

rsync-eos:
	chmod -R g+w _build/html
	rsync -rlpgoDvhz _build/html/ $(EOS_HOST):$(EOS_WEB)
	@echo "rsync to EOS public web complete."
