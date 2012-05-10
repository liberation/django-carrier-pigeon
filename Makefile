all:
	echo "Carrier Pigeon Makefile"

init:
	pip install django==1.3.0
	git submodule init
	git submodule update
