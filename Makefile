.PHONY: all dist srpm copr
FEDORA_VERSION="f25"

all:

local: dist spec
	fedpkg local

srpm: dist spec
	fedpkg --dist "$(FEDORA_VERSION)" srpm

copr: srpm
	copr-cli build network-testing `fedpkg --dist "$(FEDORA_VERSION)" verrel`.src.rpm

dist:
	python setup.py sdist
	cp dist/*.tar.gz .

spec: network-testing.spec

network-testing.spec: network-testing.spec.in test-client-server Makefile
	>$@.new
	sed $< -e '/^%description deps$$/Q' >>$@.new
	./test-client-server --deps | sed -e 's/^/Requires: /' >>$@.new
	sed $< -ne '/^%description deps$$/,$$p' >>$@.new
	mv $@.new $@

clean:
	rm -rf dist
	rm -rf *.src.rpm

vagrant:
	vagrant up --provision
	vagrant ssh
