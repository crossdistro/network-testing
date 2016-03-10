.PHONY: all dist srpm copr

all:
dist:
	python setup.py sdist
	cp dist/*.tar.gz .
srpm: dist
	fedpkg srpm
local:dist
	fedpkg local
copr: srpm
	copr-cli build network-testing `fedpkg verrel`.src.rpm
