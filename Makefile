.PHONY: all dist srpm copr

all:
local: dist spec
	fedpkg local
srpm: dist spec
	fedpkg srpm
copr: srpm
	copr-cli build network-testing `fedpkg verrel`.src.rpm

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
