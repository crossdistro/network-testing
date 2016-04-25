.PHONY: all dist srpm copr
FEDORA_VERSION="f25"

all:

run:
	rm -rf json-output
	mkdir json-output
	-sudo ./test-client-server --outdir json-output

json-output/.done:
	mkdir -p json-output
	$(MAKE) run
	touch $@

local: dist spec
	fedpkg local

srpm: dist spec
	fedpkg --dist "$(FEDORA_VERSION)" srpm

copr: srpm
	copr-cli build network-testing `fedpkg --dist "$(FEDORA_VERSION)" verrel`.src.rpm

dist:
	python setup.py sdist
	ln -sf dist/*.tar.gz .

spec: network-testing.spec

network-testing.spec: network-testing.spec.in test-client-server Makefile
	>$@.new
	sed $< -e '/^%description deps$$/Q' >>$@.new
	./test-client-server --deps | sed -e 's/^/Requires: /' >>$@.new
	sed $< -ne '/^%description deps$$/,$$p' >>$@.new
	mv $@.new $@

clean:
	rm -rf dist
	rm -rf json-output
	rm -rf html-output
	rm -rf *.src.rpm

vagrant:
	vagrant up --provision
	vagrant ssh

html: json-output/.done
	./test-client-server-genhtml

show-html: html
	xdg-open html-output/index.html
